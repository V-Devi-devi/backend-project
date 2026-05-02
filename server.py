import token

from fastapi import FastAPI,HTTPException,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel,Field,validator
from passlib.context import CryptContext
from jose import jwt,JWTError
from datetime import datetime,timedelta
app=FastAPI()
pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")
SECRET_KEY="my-super-secret-key"
ALGORITHM="HS256"
bearer_scheme = HTTPBearer()
def hash_password(password:str)->str:
    return pwd_context.hash(password)
def verify_password(plain_password:str,hashed_password:str)->bool:
    return pwd_context.verify(plain_password,hashed_password)

users_db=[]
class UserRegister(BaseModel):
    username:str
    password:str
class UserLogin(BaseModel):
    username:str
    password:str
class UserData(BaseModel):
    username:str
    password:str
def create_access_token(username:str)->str:
    payload={
        "sub":username,
        "exp":datetime.utcnow()+timedelta(minutes=30)
    }
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials  
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")
    for u in users_db:
        if u["username"] == username:
            return u
    raise HTTPException(status_code=401, detail="User not found")
@app.post("/register",status_code=201)
def register(user:UserData):
    for u in users_db:
        if u["username"]==user.username:
            raise HTTPException(status_code=400,detail="username already taken")
    hashed=hash_password(user.password)
    new_user={
        "id":len(users_db)+1,
        "username":user.username,
        "hashed_password":hashed
    }
    users_db.append(new_user)
    return{"message":f"Account created for {user.username}"}
@app.post("/login")
def login(user:UserLogin):
    found_user=None
    for u in users_db:
        if u["username"]==user.username:
            found_user=u
            break
    if not found_user:
        raise HTTPException(status_code=401,detail="Invalid username or password")
    if not verify_password(user.password, found_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token=create_access_token(user.username)
    return{"access_token": token,"token_type": "bearer"}
@app.get("/me")
def get_my_profile(current_user = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"]
    }
@app.get("/dashboard")
def get_dashboard(current_user = Depends(get_current_user)):
    return {
        "message": f"Welcome to your dashboard, {current_user['username']}!",
        "data": "This is private data only you can see"
    }