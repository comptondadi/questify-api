# app/routers/quests.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from .. import crud, models, schemas, oauth2
from ..database import get_db
from ..agent import QuestAgent

agent = QuestAgent()

router = APIRouter(
    prefix="/quests",
    tags=['Quests']
)

@router.get("/", response_model=List[schemas.Quest])
def read_quests_for_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """
    Fetches all quests for the current user and intelligently determines their
    completion status based on their category ('DAILY' or 'TASK').
    """
    quests_from_db = crud.get_quests_by_owner(db=db, owner_id=current_user.id)
    
    all_completions = db.query(models.QuestCompletion).filter(
        models.QuestCompletion.user_id == current_user.id
    ).all()

    completed_today_ids = {c.quest_id for c in all_completions if c.completion_date == date.today()}
    permanently_completed_ids = {c.quest_id for c in all_completions}

    response_quests = []
    for quest in quests_from_db:
        quest_schema = schemas.Quest.from_orm(quest)
        
        # --- FIX: Use 'category' to match the model and schema ---
        if quest.category == "DAILY":
            quest_schema.is_completed_today = quest.id in completed_today_ids
            quest_schema.is_permanently_completed = False
        elif quest.category == "TASK":
            is_done = quest.id in permanently_completed_ids
            quest_schema.is_completed_today = is_done
            quest_schema.is_permanently_completed = is_done
        
        quest_schema.streak = crud.calculate_streak_for_quest(db, quest_id=quest.id)
        response_quests.append(quest_schema)
        
    return response_quests


@router.post("/", response_model=schemas.Quest, status_code=status.HTTP_201_CREATED)
def create_quest_for_user(
    quest: schemas.QuestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    # --- FIX: Correct indentation and use 'category' ---
    print(f"DEBUG(router): User {current_user.email} creating quest: '{quest.title}' of type {quest.category}")
    new_quest = crud.create_user_quest(db=db, quest=quest, user_id=current_user.id)
    
    # Refresh is not strictly necessary but good practice to get defaults from DB
    db.refresh(new_quest)
    response_quest = schemas.Quest.from_orm(new_quest)

    print(f"DEBUG(router): Quest '{response_quest.title}' (ID: {response_quest.id}) created successfully.")
    return response_quest


@router.post("/{quest_id}/complete", response_model=schemas.UserWithInsight)
def complete_quest(
    quest_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    print(f"\n--- DEBUG(router): Entering complete_quest for quest_id: {quest_id} by user ID: {current_user.id} ---")
    
    quest = crud.get_quest_by_id(db, quest_id=quest_id)
    if not quest or quest.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found or not authorized.")
    
    xp_before = current_user.xp
    level_before = current_user.level
    
    updated_user = crud.complete_quest_for_user(db=db, quest_id=quest_id, user=current_user)

    if updated_user is None:
         # This should only happen if the quest was invalid in the first place, which we already checked.
         # This case is for extreme edge cases.
         raise HTTPException(status_code=500, detail="Could not process quest completion.")

    # Check if XP or level actually changed to determine if it was a new completion
    if updated_user.xp > xp_before or updated_user.level > level_before:
        print(f"DEBUG(router): Quest newly completed. Fetching history and calling QuestAgent.")
        
        recent_history = crud.get_recent_quest_history(db, user_id=current_user.id)
        discipline_summary = crud.get_user_discipline_summary(db, user_id=current_user.id)
        
        agent_insight = agent.get_completion_insight(
            quest_title=quest.title,
            quest_category=quest.category, # <-- FIX: Use 'category'
            user_level=updated_user.level,
            recent_history=recent_history,
            discipline_summary=discipline_summary
        )
    else:
        print(f"DEBUG(router): Quest was already completed. Providing a default insight.")
        agent_insight = {
            "dialogue": f"The chronicles already note your success on '{quest.title}' for today, Traveler. Rest and prepare for the next challenge."
        }

    print(f"--- DEBUG(router): Exiting complete_quest. ---")
    return {"user": updated_user, "insight": agent_insight}
# --- THIS IS THE NEW ENDPOINT ---
@router.post("/accept-side-quest", response_model=schemas.Quest, status_code=status.HTTP_201_CREATED)
def accept_side_quest(
    side_quest: schemas.SideQuest, # The frontend will send the details of the quest to accept
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """
    Creates a new quest in the user's log based on a side quest
    proposed by the AI agent.
    """
    print(f"DEBUG(router): User {current_user.id} accepting side quest: '{side_quest.title}'")
    
    # We can use the SideQuest schema directly to create a new quest.
    # Pydantic ensures the fields match up.
    new_quest_data = schemas.QuestCreate(
        title=side_quest.title,
        description=side_quest.description,
        category=side_quest.category,
        xp_value=side_quest.xp_value
    )
    
    new_quest = crud.create_user_quest(db=db, quest=new_quest_data, user_id=current_user.id)
    
    response_quest = schemas.Quest.from_orm(new_quest)
    return response_quest