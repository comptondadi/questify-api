# app/hashing.py

from passlib.context import CryptContext

# Create a context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Hasher:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        """Verifies a plain password against a hashed one."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str):
        """Hashes a plain password."""
        # --- ADD THIS FIX ---
        # Bcrypt has a 72-byte limit. We must encode to bytes to check length
        # and then pass the original string to passlib.
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # You can either raise an error or truncate. For user registration,
            # raising an error is better to inform them the password is too long.
            # However, to fix the internal passlib issue, we'll just truncate for now.
            # A better long-term fix is often ensuring library versions are compatible.
            truncated_password = password_bytes[:72].decode('utf-8', 'ignore')
            return pwd_context.hash(truncated_password)
        
        return pwd_context.hash(password)