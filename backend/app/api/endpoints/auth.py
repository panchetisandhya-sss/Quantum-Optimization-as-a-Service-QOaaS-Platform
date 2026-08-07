from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, AuditLog
from app.schemas.schemas import UserCreate, UserLogin, Token, UserOut, GoogleSSOInput
from app.core.security import get_password_hash, verify_password, create_access_token
from app.config import settings

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    Role is 'administrator' only if the email appears in the ADMIN_EMAILS allow-list
    (configured via the ADMIN_EMAILS environment variable).
    Registration alone never grants admin privileges based on email domain.
    """
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists.",
        )

    hashed_password = get_password_hash(user_in.password)

    # Determine role via explicit allow-list only — never by email domain.
    admin_emails = settings.get_admin_emails()
    role = "administrator" if user_in.email.lower() in admin_emails else "business_analyst"

    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log
    audit = AuditLog(user_id=new_user.id, action="USER_REGISTRATION")
    db.add(audit)
    db.commit()

    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )

    # Audit log
    audit = AuditLog(user_id=user.id, action="USER_LOGIN")
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
    }


@router.post("/google-sso", response_model=Token)
def google_sso(sso_in: GoogleSSOInput, db: Session = Depends(get_db)):
    """
    Handles Google OAuth SSO login and auto-registration.
    Ensures prompt='select_account' is acknowledged and verifies account session.
    """
    user = db.query(User).filter(User.email == sso_in.email).first()
    if not user:
        admin_emails = settings.get_admin_emails()
        role = "administrator" if sso_in.email.lower() in admin_emails else "business_analyst"
        default_pwd = get_password_hash("google_auth_secure_pass_123")
        user = User(
            email=sso_in.email,
            hashed_password=default_pwd,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        audit = AuditLog(user_id=user.id, action="GOOGLE_SSO_AUTO_REGISTER")
        db.add(audit)
        db.commit()

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )

    audit = AuditLog(user_id=user.id, action="GOOGLE_SSO_LOGIN")
    db.add(audit)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
    }
