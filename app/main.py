# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
# This is the line that brings in all your endpoints now
from .routers import auth, quests, users, discipline 
# This creates the database tables if they don't exist
models.Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Questify API",
    description="An API for forming habits through gamification.",
    version="1.0.0",
)

# --- CORS Middleware ---
origins = [
    "http://localhost:3000", # The origin for your React front-end
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
# These three lines are now responsible for all your API endpoints.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(quests.router)
app.include_router(discipline.router)


# This is the ONLY endpoint that should be in main.py
@app.get("/", tags=['Root'])
def read_root():
    return {"message": "Welcome to the Questify API"}

#
# DELETE ANY OTHER @app.post, @app.get, etc. FROM THIS FILE!
#