from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Contribution, User
from app.schemas.schemas import ContributionCreate, ContributionReview, ContributionOut
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=ContributionOut, status_code=status.HTTP_201_CREATED)
def submit_contribution(contribution: ContributionCreate, db: Session = Depends(get_db)):
    db_contrib = Contribution(
        name=contribution.name,
        email=contribution.email,
        institution=contribution.institution,
        github=contribution.github,
        title=contribution.title,
        category=contribution.category,
        description=contribution.description,
        markdown_content=contribution.markdown_content,
        code_content=contribution.code_content,
        file_path=contribution.file_path,
        status="PENDING"
    )
    db.add(db_contrib)
    db.commit()
    db.refresh(db_contrib)
    return db_contrib

@router.get("/approved", response_model=List[ContributionOut])
def get_approved_contributions(db: Session = Depends(get_db)):
    return db.query(Contribution).filter(Contribution.status == "APPROVED").all()

@router.get("/", response_model=List[ContributionOut])
def get_all_contributions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Contribution).order_by(Contribution.created_at.desc()).all()

@router.put("/{contrib_id}/review", response_model=ContributionOut)
def review_contribution(contrib_id: str, review: ContributionReview, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_contrib = db.query(Contribution).filter(Contribution.id == contrib_id).first()
    if not db_contrib:
        raise HTTPException(status_code=404, detail="Contribution not found.")
    
    if review.status not in ["APPROVED", "REJECTED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Invalid review status.")
        
    db_contrib.status = review.status
    db.commit()
    db.refresh(db_contrib)
    return db_contrib
