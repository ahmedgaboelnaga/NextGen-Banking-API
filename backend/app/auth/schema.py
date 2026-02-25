import uuid
from enum import Enum
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, field_validator
from fastapi import HTTPException, status
from backend.app.core.i18n import _


class SecurityQuestionSchema(str, Enum):
    MOTHER_MAIDEN_NAME = "mother_median_name"
    CHILDHOOD_FRIEND = "childhood friend"
    FAVORITE_COLOR = "favorite_color"
    BIRTH_CITY = "birth_city"
    FIRST_SCHOOL = "first_school"

    @classmethod
    def get_description(cls, value: "SecurityQuestionSchema") -> str:
        descriptions = {
            cls.MOTHER_MAIDEN_NAME: "What is your mother's maiden name?",
            cls.CHILDHOOD_FRIEND: "Who was your childhood friend?",
            cls.FAVORITE_COLOR: "What is your favorite color?",
            cls.BIRTH_CITY: "In which city were you born?",
            cls.FIRST_SCHOOL: "What was the name of your first school?",
        }
        return descriptions.get(value, "Unknown security question")


class AccountStatusSchema(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


class RoleChoicesSchema(str, Enum):
    CUSTOMER = "customer"
    ACCOUNT_EXECUTIVE = "account_executive"
    BRANCH_MANAGER = "branch_manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    TELLER = "teller"


class BaseUserSchema(SQLModel):
    username: str | None = Field(default=None, max_length=12, unique=True)
    email: EmailStr = Field(default=None, unique=True, index=True, max_length=255)
    first_name: str = Field(max_length=30)
    middle_name: str | None = Field(default=None, max_length=30)
    last_name: str = Field(max_length=30)
    id_no: int = Field(unique=True, gt=0)
    is_active: bool = False
    is_superuser: bool = False
    security_question: SecurityQuestionSchema = Field(max_length=30)
    security_answer: str = Field(max_length=30)
    account_status: AccountStatusSchema = Field(default=AccountStatusSchema.INACTIVE)
    role: RoleChoicesSchema = Field(default=RoleChoicesSchema.CUSTOMER)


class UserCreateSchema(BaseUserSchema):
    password: str = Field(min_length=8, max_length=40)
    confirm_password: str = Field(min_length=8, max_length=40)

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Passwords do not match"),
                    "action": _(
                        "Please ensure that the password and confirm password fields match."
                    ),
                },
            )
        return v


class UserReadSchema(BaseUserSchema):
    id: uuid.UUID
    full_name: str


class EmailRequestSchema(SQLModel):
    email: EmailStr


class LoginRequestSchema(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=40)


class OTPVerifyRequestSchema(SQLModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class PasswordResetRequestSchema(SQLModel):
    email: EmailStr


class ConfirmPasswordResetSchema(SQLModel):
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=40,
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=40,
    )

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Passwords do not match"),
                    "action": _(
                        "Please ensure that the new password and confirm new password fields match."
                    ),
                },
            )
        return v
