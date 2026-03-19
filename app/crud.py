# app/crud.py
import requests
from sqlalchemy.orm import Session, joinedload
from . import models, schemas, hashing
from datetime import date, datetime, timedelta
from typing import Optional

# =============================================================================
#                              USER CRUD
# =============================================================================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = hashing.Hasher.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# =============================================================================
#                              QUEST CRUD
# =============================================================================

def get_quest_by_id(db: Session, quest_id: int):
    return db.query(models.Quest).filter(models.Quest.id == quest_id).first()

def get_quests_by_owner(db: Session, owner_id: int):
    return db.query(models.Quest).filter(models.Quest.owner_id == owner_id).all()

def create_user_quest(db: Session, quest: schemas.QuestCreate, user_id: int):
    """Creates a new quest for a user, including the category."""
    db_quest = models.Quest(
        title=quest.title,
        description=quest.description,
        xp_value=quest.xp_value,
        owner_id=user_id, # <-- COMMA WAS MISSING HERE
        category=quest.category
    )
    db.add(db_quest)
    db.commit()
    db.refresh(db_quest)
    return db_quest

# =============================================================================
#                         DISCIPLINE ENGINE LOGIC
# =============================================================================

def calculate_streak_for_quest(db: Session, quest_id: int):
    """Calculates the current consecutive day streak for a given quest."""
    completions = db.query(models.QuestCompletion.completion_date).filter(
        models.QuestCompletion.quest_id == quest_id
    ).distinct().order_by(models.QuestCompletion.completion_date.desc()).all()

    if not completions:
        return 0

    dates = [comp.completion_date for comp in completions]
    today = date.today()
    streak = 0
    
    if dates[0] == today or dates[0] == (today - timedelta(days=1)):
        streak = 1
        for i in range(len(dates) - 1):
            if (dates[i] - dates[i+1]).days == 1:
                streak += 1
            else:
                break
    return streak

def get_user_discipline_summary(db: Session, user_id: int) -> dict:
    """
    Generates a summary of the user's recent performance to provide context for the AI agent.
    """
    print(f"--- DEBUG: Generating discipline summary for User ID: {user_id} ---")
    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    # Count completions today
    completions_today = db.query(models.QuestCompletion).filter(
        models.QuestCompletion.user_id == user_id,
        models.QuestCompletion.completion_date == today
    ).count()
    print(f"DEBUG: Completions today: {completions_today}")

    # Count completions in the last 7 days
    completions_this_week = db.query(models.QuestCompletion).filter(
        models.QuestCompletion.user_id == user_id,
        models.QuestCompletion.completion_date >= seven_days_ago
    ).count()
    print(f"DEBUG: Completions this week: {completions_this_week}")
    
    # This is a placeholder for a more complex query to find the favorite category
    # For now, we'll just return a default value.
    favorite_category = "learning" 

    summary = {
        "completions_today": completions_today,
        "completions_this_week": completions_this_week,
        "favorite_category": favorite_category,
    }
    print(f"DEBUG: Discipline summary generated: {summary}")
    return summary

def complete_quest_for_user(db: Session, quest_id: int, user: models.User):
    """
    Handles the logic for a user completing a quest.
    """
    print(f"\n--- DEBUG START: complete_quest_for_user (Quest ID: {quest_id}, User ID: {user.id}) ---")
    quest = get_quest_by_id(db, quest_id=quest_id)
    if not quest or quest.owner_id != user.id:
        return None

    today = date.today()
    existing_completion = db.query(models.QuestCompletion).filter(
        models.QuestCompletion.quest_id == quest_id,
        models.QuestCompletion.user_id == user.id,
        models.QuestCompletion.completion_date == today
    ).first()

    if existing_completion:
        print(f"DEBUG: Quest {quest_id} already completed today. Returning user unchanged.")
        return user

    xp_to_add = quest.xp_value
    user.xp += xp_to_add
    
    old_level = user.level
    while user.xp >= (user.level * 100):
        xp_needed = user.level * 100
        user.level += 1
        user.xp -= xp_needed
        print(f"DEBUG: User {user.id} leveled up to Level {user.level}! Remaining XP: {user.xp}")

    if user.level > old_level:
        n8n_webhook_url = "http://localhost:5678/webhook-test/380a3990-08dd-4afe-98e4-584aa04af985"
        try:
            payload = {"username": user.username, "email": user.email, "new_level": user.level}
            requests.post(n8n_webhook_url, json=payload)
        except requests.exceptions.RequestException as e:
            print(f"Could not send n8n webhook: {e}")

    completion_log = models.QuestCompletion(
        quest_id=quest_id,
        user_id=user.id,
        xp_awarded=xp_to_add
    )
    db.add(completion_log)

    db.commit()
    db.refresh(user)
    print(f"--- DEBUG END: complete_quest_for_user ---")
    return user

def get_recent_quest_history(db: Session, user_id: int, limit: int = 5) -> str:
    """
    Fetches the user's recent quest history to provide context for the AI agent.
    Returns a formatted string.
    """
    three_days_ago = datetime.utcnow() - timedelta(days=3)

    recent_completions = db.query(models.QuestCompletion).options(
        joinedload(models.QuestCompletion.quest)
    ).filter(
        models.QuestCompletion.user_id == user_id,
        models.QuestCompletion.completion_timestamp >= three_days_ago
    ).order_by(models.QuestCompletion.completion_timestamp.desc()).limit(limit).all()
    
    if not recent_completions:
        return "No recent activity."

    history = []
    for comp in recent_completions:
        time_since = datetime.utcnow() - comp.completion_timestamp
        hours_ago = time_since.total_seconds() / 3600
        if hours_ago < 1:
            time_str = f"{int(hours_ago * 60)} minutes ago"
        elif hours_ago < 24:
            time_str = f"{int(hours_ago)} hours ago"
        else:
            time_str = f"{int(hours_ago / 24)} days ago"

        history.append(
            f"- Completed '{comp.quest.title}' (Category: {comp.quest.category}) {time_str}."
        )
    
    return "\n".join(history)