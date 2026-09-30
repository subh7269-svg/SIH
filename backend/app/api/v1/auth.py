from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserLogin, TokenResponse, UserResponse
from backend.app.core.security import create_access_token, verify_password, get_password_hash
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Check default investigator fallback or DB user
    user = db.query(User).filter(User.username == login_data.username).first()
    
    # Auto-seed default investigator if not present
    if not user and login_data.username in ("investigator", "admin"):
        valid_demo_passwords = ("leadforge2026", "tracex2026")
        if login_data.password in valid_demo_passwords:
            role = "ADMIN" if login_data.username == "admin" else "INVESTIGATOR"
            user = User(
                id=str(uuid.uuid4()),
                username=login_data.username,
                email=f"{login_data.username}@leadforge.local",
                hashed_password=get_password_hash("leadforge2026"),
                role=role,
                full_name="Lead Cyber Investigator" if role == "INVESTIGATOR" else "System Administrator",
                badge_number="LF-9041"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. (Default demo: investigator / leadforge2026)"
        )

    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(db: Session = Depends(get_db)):
    # Returns default analyst profile
    user = db.query(User).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            username="investigator",
            email="investigator@leadforge.local",
            hashed_password=get_password_hash("leadforge2026"),
            role="INVESTIGATOR",
            full_name="Lead Cyber Investigator",
            badge_number="LF-9041"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserResponse.model_validate(user)
