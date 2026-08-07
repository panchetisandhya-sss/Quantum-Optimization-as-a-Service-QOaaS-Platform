import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import OptimizationJob, User, AuditLog
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/reports/{job_id}/download")
def download_pdf_report(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download the generated executive PDF report for an optimization job.
    """
    job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found.")
        
    pdf_path = job.encrypted_pdf_path or f"/home/rgukt/.gemini/antigravity/scratch/qoaas-platform/backend/reports/{job_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report file not found on server.")
        
    # Log Audit event
    audit = AuditLog(user_id=current_user.id, action=f"DOWNLOAD_PDF_REPORT_{job_id}")
    db.add(audit)
    db.commit()
    
    filename = f"optimized_report_{job_id}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename
    )

# Backward-compatibility alias so any client fetching /download-decrypted still gets the report directly
@router.get("/reports/{job_id}/download-decrypted")
def download_decrypted_pdf_alias(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return download_pdf_report(job_id=job_id, db=db, current_user=current_user)
