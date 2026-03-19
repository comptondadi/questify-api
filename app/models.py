# In app/models.py

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import date, datetime # Make sure both are imported

# =============================================================================
#                                USER MODEL
# =============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    last_seen = Column(Date, default=date.today)

    # Establishes the one-to-many relationship: One User has many Quests.
    quests = relationship("Quest", back_populates="owner", cascade="all, delete-orphan")
    # Establishes the one-to-many relationship: One User has many QuestCompletions.
    quest_completions = relationship("QuestCompletion", back_populates="user")

# =============================================================================
#                                QUEST MODEL
# =============================================================================

class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    xp_value = Column(Integer, default=10)
    owner_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String, default="GENERAL", nullable=False) # e.g., "general", "redemption", "challenge"
    # Optional advanced columns you considered
    # level_assigned = Column(Integer, nullable=True, index=True) 
    # is_active = Column(Boolean, default=True, nullable=False)

    # Establishes the many-to-one relationship back to the User.
    owner = relationship("User", back_populates="quests")
    # Establishes the one-to-many relationship: One Quest has many Completions.
    completions = relationship("QuestCompletion", back_populates="quest", cascade="all, delete-orphan")

# =============================================================================
#                           QUEST COMPLETION MODEL
# =============================================================================

class QuestCompletion(Base):
    __tablename__ = "quest_completions"

    id = Column(Integer, primary_key=True, index=True)
    
    # --- THIS IS THE CRITICAL FIX ---
    # The 'completion_date' column needs a default value to be set automatically.
    completion_timestamp = Column(DateTime, default=datetime.utcnow) 
    completion_date = Column(Date, default=date.today, index=True) # <-- FIX APPLIED HERE

    # Foreign Keys to link this record to a specific Quest and User
    quest_id = Column(Integer, ForeignKey("quests.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    xp_awarded = Column(Integer, nullable=False) 

    # Establishes the many-to-one relationship back to the Quest.
    quest = relationship("Quest", back_populates="completions")
    # Establishes the many-to-one relationship back to the User.
    user = relationship("User", back_populates="quest_completions")