# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import crud, models, schemas, oauth2 # We will create oauth2.py
from ..database import get_db # Import get_db from database.py
# ...

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

# Route to create a new user (Sign up)
@router.post("/", response_model=schemas.User)
def create_new_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already taken")
        
    return crud.create_user(db=db, user=user)

# Route to get the currently logged-in user's details
@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(oauth2.get_current_user)):
    return current_user