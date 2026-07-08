from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from datetime import date, datetime, timedelta

from pwdlib import PasswordHash
from pwdlib.exceptions import VerificationError

from sqlalchemy import select
from sqlalchemy.orm import Session

from dotenv import load_dotenv
import os

import jwt

from app.main import app
from app.database.connection import get_db
from app.database.models import UserModel


load_dotenv()

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

pwd_hasher = PasswordHash.recommended()

SECRET_KEY = os.getenv("JWT_KEY")

@app.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    stmt = select(UserModel).where((UserModel.username == request.username) | (UserModel.email == request.email))
    existing = db.execute(stmt).scalar_one_or_none()

    if existing: 
        if existing.username:

            raise HTTPException(status_code=409, detail="Username already in use")
        if existing.email:
            raise HTTPException(status_code=409, detail="Email already in use")
    
    hashed_password = pwd_hasher.hash(request.password)
    new_user = UserModel(
        username = request.username,
        email = request.email,
        hashed_password = hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        'user_id': new_user.id,
        'username': new_user.username,
        'email': new_user.email
    }

