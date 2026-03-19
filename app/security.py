# in app/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional

# --- ADD THESE IMPORTS ---
from passlib.context import CryptContext
from jose import JWTError, jwt
# -------------------------

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import crud, models, database, schemas 

# ===================================================================
# ===== START: ADD THIS ENTIRE PASSWORD HASHING BLOCK =============
# ===================================================================

# 1. We define the hashing algorithm we want to use (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. This function takes a plain password and returns its hashed version
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 3. This function takes a plain password and a hashed password and checks if they match
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ===================================================================
# ===== END: PASSWORD HASHING BLOCK =================================
# ===================================================================


# --- JWT Token Handling (You already have this part below) ---
# THIS SHOULD BE A SECRET KEY, loaded from environment variables in a real app
SECRET_KEY = "a_very_secret_key_for_questify" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Get Current User Dependency (You already have this) ---
# This tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # In JWT standard, the subject is stored in the "sub" claim
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user