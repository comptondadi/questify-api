# app/routers/discipline.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from .. import crud, models, schemas, oauth2
from ..database import get_db
from ..agent import QuestAgent

agent = QuestAgent()

router = APIRouter(
    prefix="/discipline",
    tags=['Discipline Engine']
)

@router.post("/check-in", response_model=schemas.User)
def daily_check_in(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """
    This endpoint is called when the user opens the app. It checks if the
    user has been seen today. If not, it can trigger events like creating
    a 'Redemption Quest' for inactive users via the AI agent.
    """
    today = date.today()
    
    if not current_user.last_seen or current_user.last_seen < today:
        
        if current_user.last_seen:
            days_missed = (today - current_user.last_seen).days
            
            # --- THIS IS THE CORRECTED LOGIC ---
            # If the user has been inactive for a significant period
            if days_missed > 2:
                print(f"User {current_user.id} has been inactive for {days_missed} days. Calling agent for re-engagement plan.")
                
                # Get context for the agent
                discipline_summary = crud.get_user_discipline_summary(db, user_id=current_user.id)
                
                # Call the agent to get the re-engagement plan
                reengagement_insight = agent.get_reengagement_insight(
                    user_level=current_user.level,
                    days_missed=days_missed,
                    discipline_summary=discipline_summary
                )

                # Create the Redemption Quest proposed by the agent
                if reengagement_insight and reengagement_insight.get("redemption_quest"):
                    quest_data = reengagement_insight["redemption_quest"]
                    # Use Pydantic's model_validate to handle potential extra fields
                    redemption_quest_schema = schemas.QuestCreate.model_validate(quest_data)
                    crud.create_user_quest(db, quest=redemption_quest_schema, user_id=current_user.id)
                    
                    # Log the agent's nudge for debugging
                    print(f"AGENT NUDGE: {reengagement_insight.get('dialogue')}")
        
        # Update the user's last seen date to today regardless
        current_user.last_seen = today
        db.commit()
        db.refresh(current_user)
        
    return current_user