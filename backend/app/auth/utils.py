import random
import string
from backend.app.core.config import settings
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def generate_otp(length=6) -> str:
    """Generate a random OTP of specified length."""
    return ''.join(random.choices(string.digits, k=length))


def generate_password_hash(password: str) -> str:
    """Hash the password using Argon2."""
    return _ph.hash(password)


def verify_password_hash(password: str, hashed_password: str) -> bool:
    """Verify the password against the hashed password."""
    try:
        return _ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False

def generate_username() -> str:
    """Generate a random username."""
    bank_name = settings.SITE_NAME
    words = bank_name.split()
    prefix = "".join([word[0] for word in words]).upper()
    remaining_length = 12 - len(prefix) - 1
    random_string = "".join(random.choices(string.ascii_uppercase + string.digits, k=remaining_length))
    return f"{prefix}-{random_string}"