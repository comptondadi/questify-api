# app/schemas.py

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import date

# =============================================================================
#                              USER SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    level: int
    xp: int

    # --- Pydantic V2 Update ---
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
#                              QUEST SCHEMAS
# =============================================================================

class QuestBase(BaseModel):
    title: str
    description: Optional[str] = None
    xp_value: int = 10
    category: str = "GENERAL"

class QuestCreate(QuestBase):
    pass

class Quest(QuestBase):
    id: int
    owner_id: int
    is_completed_today: bool = False
    is_permanently_completed: bool = False
    streak: int = 0
    # 'category' is inherited from QuestBase, so no need to repeat it here.

    # --- Pydantic V2 Update (with correct indentation) ---
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
#                              TOKEN SCHEMAS
# =============================================================================
 
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# =============================================================================
#                       RESPONSE MODEL FOR AGENT INSIGHT
# =============================================================================



class SideQuest(BaseModel):
    title: str
    description: str
    category: str
    xp_value: int
    resource_link: str

     # --- Pydantic V2 Update ---
class AgentInsight(BaseModel):
    dialogue: str
    side_quest: Optional[SideQuest] = None
    bonus_xp: Optional[int] = None
    side_quest_title: Optional[str] = None
    side_quest_details: Optional[str] = None
    resource_link: Optional[str] = None
    
    # --- Pydantic V2 Update ---
    model_config = ConfigDict(from_attributes=True)


class UserWithInsight(BaseModel):
    user: User
    insight: AgentInsight

    # --- Pydantic V2 Update ---
    model_config = ConfigDict(from_attributes=True)