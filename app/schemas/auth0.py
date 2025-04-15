from pydantic import BaseModel
from typing import List


class UserClaims(BaseModel):
    sub: str
    email: str
    name: str
    given_name: str
    family_name: str
    picture: str
    permissions: List[str]
