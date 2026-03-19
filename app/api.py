# app/api.py
from datetime import timedelta
from typing import List

# ... other imports
from fastapi import APIRouter, Depends, HTTPException, status
# This is the important part
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel import Session
from jose import JWTError, jwt

from . import crud, models, security, gamification
from .database import get_session
from .security import SECRET_KEY, ALGORITHM

# The scheme should be defined once
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    # ... the rest of the function is correct ...
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = models.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(session, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# --- API Router ---
router = APIRouter()

# --- Authentication Endpoints ---
@router.post("/token", response_model=models.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)
):
    user = crud.get_user_by_username(session, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Endpoints ---
@router.post("/users/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: models.UserCreate, session: Session = Depends(get_session)):
    db_user = crud.get_user_by_username(session, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(session=session, user=user)

@router.get("/users/me", response_model=models.UserReadWithDetails, tags=["Users"])
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- Task Endpoints ---
@router.post("/tasks/", response_model=models.TaskRead, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
def create_task(
    task: models.TaskCreate,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return crud.create_user_task(session=session, task=task, user_id=current_user.id)

@router.get("/tasks/", response_model=List[models.TaskRead], tags=["Tasks"])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tasks = crud.get_tasks_by_user(session, user_id=current_user.id, skip=skip, limit=limit)
    return tasks

@router.put("/tasks/{task_id}", response_model=models.TaskRead, tags=["Tasks"])
def update_task(
    task_id: int,
    task_update: models.TaskUpdate,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_task = crud.get_task(session, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")
    
    # Gamification logic
    if task_update.is_completed and not db_task.is_completed:
        current_user.xp += db_task.xp_value
        gamification.check_for_level_up(current_user)
        gamification.check_and_award_badges(session, current_user)
        session.add(current_user) # Add user to session to save changes

    task_data = task_update.model_dump(exclude_unset=True)
    for key, value in task_data.items():
        setattr(db_task, key, value)
    
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    session.refresh(current_user) # Refresh user to get latest xp/level
    return db_task

# --- Gamification & AI Endpoints ---
@router.get("/quests/daily-suggestions", tags=["AI Quests"])
def get_daily_quests(current_user: models.User = Depends(get_current_user)):
    """Provides a list of suggested daily quests from the AI."""
    suggester = gamification.AIQuestSuggester(user=current_user)
    return suggester.suggest_quests()

@router.get("/badges", response_model=List[models.Badge], tags=["Gamification"])
def get_all_badges(session: Session = Depends(get_session)):
    """Returns a list of all possible badges in the game."""
    return crud.get_badges(session)