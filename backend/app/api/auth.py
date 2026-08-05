from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.schemas.auth import (
    UserCreate,
    UserResponse,
    Token,
    TokenData,
    PasswordReset,
    PasswordResetRequest,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = structlog.get_logger()
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# Mock user database - replace with Firestore
MOCK_USERS_DB = {}


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate):
    """Register a new user"""
    logger.info("user_registration_attempt", email=user_data.email)

    # Check if user exists
    if user_data.email in MOCK_USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user_id = f"user_{len(MOCK_USERS_DB) + 1}"
    hashed_password = get_password_hash(user_data.password)

    user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "hashed_password": hashed_password,
        "role": "user",
        "subscription": {
            "tier": "free",
            "expires_at": datetime.utcnow() + timedelta(days=30),
        },
        "risk_profile": {
            "max_risk_per_trade": 2.0,
            "max_daily_loss": 5.0,
            "max_position_size": 10.0,
        },
        "preferences": {
            "theme": "system",
            "default_index": "NIFTY",
            "notifications": {
                "email": True,
                "telegram": False,
                "browser": True,
                "alerts": {
                    "ema_cross": True,
                    "vwap_cross": True,
                    "breakout": True,
                    "oi_spike": False,
                    "pcr_shift": False,
                    "volume_spike": True,
                },
            },
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    MOCK_USERS_DB[user_data.email] = user

    logger.info("user_registered", user_id=user_id, email=user_data.email)

    return UserResponse(**{k: v for k, v in user.items() if k != "hashed_password"})


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    logger.info("login_attempt", username=form_data.username)

    user = MOCK_USERS_DB.get(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"]}
    )
    refresh_token = create_refresh_token(data={"sub": user["email"]})

    logger.info("login_success", user_id=user["id"])

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    payload = decode_token(refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    email = payload.get("sub")
    user = MOCK_USERS_DB.get(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(data={"sub": email, "user_id": user["id"]})
    new_refresh_token = create_refresh_token(data={"sub": email})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post("/password-reset-request")
async def request_password_reset(data: PasswordResetRequest):
    """Request password reset"""
    logger.info("password_reset_requested", email=data.email)

    # In production, send email with reset link
    # For now, just return success
    return {"message": "Password reset email sent if account exists"}


@router.post("/password-reset")
async def reset_password(data: PasswordReset):
    """Reset password with token"""
    logger.info("password_reset_attempt")

    payload = decode_token(data.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    email = payload.get("sub")
    user = MOCK_USERS_DB.get(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user["hashed_password"] = get_password_hash(data.new_password)
    user["updated_at"] = datetime.utcnow()

    logger.info("password_reset_success", user_id=user["id"])

    return {"message": "Password reset successful"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user profile"""
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    email = payload.get("sub")
    user = MOCK_USERS_DB.get(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(**{k: v for k, v in user.items() if k != "hashed_password"})
