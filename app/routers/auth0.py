import asyncio
import logging
import requests
from fastapi import APIRouter, HTTPException, Query, Depends
from starlette.responses import RedirectResponse
from fastapi.concurrency import run_in_threadpool

from app.core.config import auth0_settings
from app.services.auth0_service import (
    decode_and_update_db,
    validate_token,
    get_auth0_token,
)
from app.schemas.auth0 import UserClaims

router = APIRouter(prefix="/auth0", tags=["Auth0 Authentication"])
logger = logging.getLogger(__name__)


@router.get("/login")
def auth0_login():
    auth_url = (
        f"{auth0_settings.AUTH0_AUTHORIZATION_ENDPOINT}"
        f"?response_type=code"
        f"&client_id={auth0_settings.AUTH0_CLIENT_ID}"
        f"&redirect_uri={auth0_settings.AUTH0_REDIRECT_URI}"
        f"&scope=offline_access openid profile email"
        f"&audience={auth0_settings.AUTH0_AUDIENCE}"
    )
    return RedirectResponse(auth_url)


@router.get("/token")
async def auth0_get_access_token(code: str = Query(...)):
    payload = {
        "grant_type": "authorization_code",
        "client_id": auth0_settings.AUTH0_CLIENT_ID,
        "client_secret": auth0_settings.AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": auth0_settings.AUTH0_REDIRECT_URI,
    }
    headers = {"content-type": "application/x-www-form-urlencoded"}

    response = await run_in_threadpool(
        requests.post,
        auth0_settings.AUTH0_TOKEN_ENDPOINT,
        data=payload,
        headers=headers,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    token_data = response.json()
    asyncio.create_task(decode_and_update_db(token_data))
    return token_data


@router.post("/token/client")
async def auth0_token():
    try:
        token = get_auth0_token()
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protected")
def protected(user_claims: UserClaims = Depends(validate_token)):
    return user_claims
