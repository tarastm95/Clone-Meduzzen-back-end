import logging
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jws, jwt, ExpiredSignatureError, JWTError, JWSError
from jose.exceptions import JWTClaimsError
from typing import Annotated
from sqlalchemy.future import select

from app.core.config import auth0_settings
from app.db.database import AsyncSessionLocal
from app.db.models.user import User, Auth0User
from app.schemas.auth0 import UserClaims

logger = logging.getLogger(__name__)
security = HTTPBearer()

jwks = requests.get(auth0_settings.AUTH0_JWKS_ENDPOINT).json()["keys"]


def get_auth0_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": auth0_settings.AUTH0_CLIENT_ID,
        "client_secret": auth0_settings.AUTH0_CLIENT_SECRET,
        "audience": auth0_settings.AUTH0_AUDIENCE,
    }
    headers = {"content-type": "application/x-www-form-urlencoded"}

    response = requests.post(
        auth0_settings.AUTH0_TOKEN_ENDPOINT, data=payload, headers=headers
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json().get("access_token")


def find_public_key(kid: str):
    for key in jwks:
        if key["kid"] == kid:
            return key
    return None


def validate_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    try:
        unverified_headers = jws.get_unverified_header(credentials.credentials)
        jwt.decode(
            token=credentials.credentials,
            key=find_public_key(unverified_headers["kid"]),
            audience=auth0_settings.AUTH0_AUDIENCE,
            algorithms=["RS256"],
        )
        userinfo_response = requests.get(
            f"https://{auth0_settings.AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=401, detail="error.unauthorized")
        userinfo = userinfo_response.json()
        return UserClaims(
            sub=userinfo.get("sub", ""),
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
            given_name=userinfo.get("given_name", ""),
            family_name=userinfo.get("family_name", ""),
            picture=userinfo.get("picture", ""),
            permissions=[],
        )
    except (ExpiredSignatureError, JWTError, JWTClaimsError, JWSError) as error:
        raise HTTPException(status_code=401, detail="error.auth.couldNotValidate")


async def decode_and_update_db(token_data: dict):
    logger.info("Starting background task for processing id_token")
    id_token = token_data.get("id_token")
    if not id_token:
        logger.error("id_token is missing in token_data")
        return

    try:
        unverified_header = jwt.get_unverified_header(id_token)
        public_key = find_public_key(unverified_header.get("kid"))
        if not public_key:
            logger.error(
                "Public key not found for kid: %s", unverified_header.get("kid")
            )
            return
        decoded_token = jwt.decode(
            token=id_token,
            key=public_key,
            audience=auth0_settings.AUTH0_CLIENT_ID,
            algorithms=["RS256"],
        )
        logger.info("Decoded token: %s", decoded_token)
    except Exception as e:
        logger.exception("Error decoding id_token: %s", e)
        return

    auth0_sub = decoded_token.get("sub")
    email = decoded_token.get("email")
    name = decoded_token.get("name")
    given_name = decoded_token.get("given_name")
    family_name = decoded_token.get("family_name")
    picture = decoded_token.get("picture")
    email_verified = decoded_token.get("email_verified", False)

    if not email or not auth0_sub:
        logger.error("Mandatory data missing: email=%s, sub=%s", email, auth0_sub)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            user = User(
                auth0_sub=auth0_sub, email=email, name=name, profile_picture=picture
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Created new user: %s", user.email)
        else:
            user.auth0_sub = auth0_sub
            user.name = name
            user.profile_picture = picture
            await db.commit()
            logger.info("Updated user data: %s", user.email)

        result2 = await db.execute(
            select(Auth0User).where(Auth0User.auth0_sub == auth0_sub)
        )
        auth0_user = result2.scalars().first()
        if not auth0_user:
            auth0_user = Auth0User(
                user_id=user.id,
                auth0_sub=auth0_sub,
                email_verified=email_verified,
            )
            db.add(auth0_user)
            await db.commit()
            logger.info("Created Auth0User record for user: %s", user.email)
        else:
            logger.info("Auth0User record already exists for user: %s", user.email)
