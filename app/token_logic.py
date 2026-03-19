# app/token_logic.py

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from . import schemas
from .config import settings

# --- Configuration ---
# IMPORTANT: In a real app, load these from environment variables or a config file.
# NEVER hardcode secrets in your code for production.
SECRET_KEY = "a_very_secret_key_for_your_project_change_it_now"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token will be valid for 60 minutes

def create_access_token(data: dict):
    """
    Generates a new JWT access token.
    """
    to_encode = data.copy()
    # Set the expiration time for the token
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Encode the token with your data, secret key, and algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    """
    Verifies a JWT token and returns the username from its payload.
    Raises the provided exception if the token is invalid.
    """
    try:
        # Decode the token using your secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # The "sub" (subject) claim should contain the username
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # You can also check the expiration time here, though jwt.decode does it automatically.
        
        # Return the validated token data
        return schemas.TokenData(username=username)
    except JWTError:
        # If decoding fails for any reason (bad signature, expired, etc.)
        raise credentials_exception