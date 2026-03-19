# app/oauth2.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from . import token_logic, crud, models
from sqlalchemy.orm import Session
from .database import get_db # Import get_db from database.py
# ...

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = token_logic.verify_token(token, credentials_exception)
    
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user