import os
from jose import jwt, JWTError
from datetime import datetime, timedelta, UTC

SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-dev-key-change-in-prod')
ALGORITHM  = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

#SECRET_KEY = "change-this-in-production-use-a-long-random-string"
#ALGORITHM = "HS256"
#ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> str:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if not username:
        raise JWTError("Token has no subject")
    return username