# app/gamification.py
from typing import List
from sqlmodel import Session
from . import models, crud

# --- Leveling System ---
def get_xp_for_next_level(level: int) -> int:
    """Calculates the XP required to reach the next level."""
    return 100 * (level ** 2)

def check_for_level_up(db_user: models.User) -> bool:
    """Checks if the user has enough XP to level up and updates them."""
    leveled_up = False
    xp_needed = get_xp_for_next_level(db_user.level)
    while db_user.xp >= xp_needed:
        db_user.level += 1
        db_user.xp -= xp_needed
        xp_needed = get_xp_for_next_level(db_user.level)
        leveled_up = True
    return leveled_up


# --- Badge System ---
def check_and_award_badges(session: Session, db_user: models.User):
    """Checks user's progress and awards badges if criteria are met."""
    all_badges = crud.get_badges(session)
    user_badge_ids = {badge.id for badge in db_user.badges}

    # Badge 1: "First Quest"
    first_quest_badge = next((b for b in all_badges if b.name == "First Quest"), None)
    if first_quest_badge and first_quest_badge.id not in user_badge_ids:
        completed_tasks = [task for task in db_user.tasks if task.is_completed]
        if len(completed_tasks) >= 1:
            db_user.badges.append(first_quest_badge)

    # Badge 2: "Productivity Novice"
    novice_badge = next((b for b in all_badges if b.name == "Productivity Novice"), None)
    if novice_badge and novice_badge.id not in user_badge_ids:
        completed_tasks = [task for task in db_user.tasks if task.is_completed]
        if len(completed_tasks) >= 5:
            db_user.badges.append(novice_badge)
    
    # Add more badge logic here...

# --- AI Quest Suggester (Mock) ---
class AIQuestSuggester:
    
    def __init__(self, user: models.User):
        self.user = user
        self.common_quests = [
            "Organize your desk for 15 minutes",
            "Go for a 20-minute walk",
            "Read one chapter of a book",
            "Drink 8 glasses of water today",
            "Spend 10 minutes meditating",
            "Plan your tasks for tomorrow",
        ]

    def suggest_quests(self, count: int = 3) -> List[dict]:
        """Suggests a list of quests for the user."""
        # Simple logic: suggest common quests not recently completed.
        # A real AI would analyze past tasks, habits, and stated goals.
        
        user_tasks_content = {task.content.lower() for task in self.user.tasks}
        suggestions = []
        
        for quest in self.common_quests:
            if quest.lower() not in user_tasks_content and len(suggestions) < count:
                suggestions.append({"content": quest, "xp_value": 15})

        # Fill up with remaining if not enough unique suggestions
        remaining_needed = count - len(suggestions)
        if remaining_needed > 0:
            for i in range(remaining_needed):
                 suggestions.append({"content": f"Complete a small personal goal {i+1}", "xp_value": 10})
        
        return suggestions