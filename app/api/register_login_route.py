from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

from datetime import date, datetime, timedelta, timezone

from pwdlib import PasswordHash

from sqlalchemy import select
from sqlalchemy.orm import Session

from dotenv import load_dotenv
import os

import jwt


from app.database.connection import get_db
from app.database.models import UserModel, EndoscopistLookup


load_dotenv()
SECRET_KEY = os.getenv("JWT_KEY")
ALGORITHM = os.getenv("ALGORITHM")

##########
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


#get current user function
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
        
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    except jwt.exceptions.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token: {e}")
        

    user = db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

##########



router = APIRouter(tags=["register and login"])

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    endoscopist_name: str

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

pwd_hasher = PasswordHash.recommended()



@router.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    stmt = select(UserModel).where((UserModel.username == request.username) | (UserModel.email == request.email))
    existing = db.execute(stmt).scalar_one_or_none()

    if existing: 
        if existing.username:

            raise HTTPException(status_code=409, detail="Username already in use")
        if existing.email:
            raise HTTPException(status_code=409, detail="Email already in use")


    
    hashed_password = pwd_hasher.hash(request.password)

    endoscopist = EndoscopistLookup(endoscopist_name = request.endoscopist_name, is_active=True)
    db.add(endoscopist)
    db.flush()

    new_user = UserModel(
        username = request.username,
        email = request.email,
        hashed_password = hashed_password,
        endoscopist_id = endoscopist.endoscopist_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        'user_id': new_user.id,
        'username': new_user.username,
        'email': new_user.email
    }

@router.post("/login")
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(UserModel).where((UserModel.username == request.username_or_email) | (UserModel.email == request.username_or_email))
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    

    
    if not pwd_hasher.verify(request.password, user.hashed_password):
    
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        'access_token': token,
        'token_type': 'bearer'
    }

