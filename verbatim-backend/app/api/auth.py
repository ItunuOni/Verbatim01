from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.database import get_supabase_client
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
settings = get_settings()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate):
    """Register a new user"""
    supabase = get_supabase_client()

    # Check if user already exists
    existing_user = supabase.table("users").select("*").eq("email", user.email).execute()
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = get_password_hash(user.password)

    # Create user in database
    new_user = supabase.table("users").insert({
        "email": user.email,
        "name": user.name,
        "password_hash": hashed_password,
        "plan_type": "free"
    }).execute()

    if not new_user.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    user_data = new_user.data[0]

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["email"], "user_id": user_data["id"]},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        user=UserResponse(**user_data)
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password"""
    supabase = get_supabase_client()

    # Get user by email
    result = supabase.table("users").select("*").eq("email", credentials.email).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user = result.data[0]

    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        user=UserResponse(**user)
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get the current authenticated user"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    email = payload.get("sub")
    user_id = payload.get("user_id")

    if email is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    supabase = get_supabase_client()
    result = supabase.table("users").select("*").eq("id", user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return result.data[0]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**current_user)
