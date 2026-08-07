"""
api/endpoints/upload.py — Phase 3: Bulk employee roster upload endpoint.

POST /api/v1/upload/employees
  - Accepts multipart/form-data with a 'file' field (.csv or .pdf)
  - Validates file size (≤50 MB) and format
  - Returns parsed employees on success or field-level errors on failure
  - Protected: requires valid Bearer token
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.services.file_parser import parse_employee_file

router = APIRouter()


@router.post("/upload/employees")
async def upload_employees(
    file: UploadFile = File(..., description="Employee roster as .csv or .pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Parse a bulk employee roster file (CSV or PDF).

    On success:
      { "valid": true, "count": N, "employees": [...] }

    On validation errors:
      { "valid": false, "count": 0, "errors": [{"row": N, "field": "...", "issue": "..."}, ...] }

    HTTP 413 if file exceeds 50 MB.
    HTTP 400 if the file type is not .csv or .pdf.
    HTTP 401 if unauthenticated.
    """
    MAX_SIZE = 50 * 1024 * 1024  # 50 MB

    filename = file.filename or "upload"
    file_bytes = await file.read()

    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({len(file_bytes) // (1024 * 1024)} MB). Maximum allowed is 50 MB.",
        )

    lower_name = filename.lower()
    if not (lower_name.endswith(".csv") or lower_name.endswith(".pdf")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{filename}'. Please upload a .csv or .pdf file.",
        )

    employees, errors = parse_employee_file(file_bytes, filename)

    if errors:
        return {
            "valid": False,
            "count": 0,
            "employees": [],
            "errors": errors,
        }

    return {
        "valid": True,
        "count": len(employees),
        "employees": employees,
        "errors": [],
    }


@router.post("/upload/finance")
async def upload_finance(
    file: UploadFile = File(..., description="Finance data as .csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Parse and classify an uploaded finance CSV file.
    Returns detected problem_type (portfolio_prices, portfolio_returns, budget_allocation)
    along with normalized records and detected field mappings.
    """
    from app.services.schema_detector import parse_and_validate_finance_csv
    filename = file.filename or "finance_upload.csv"
    file_bytes = await file.read()

    processed_payload, errors, schema_info = parse_and_validate_finance_csv(file_bytes, filename)

    if errors:
        return {
            "valid": False,
            "errors": errors
        }

    return {
        "valid": True,
        "payload": processed_payload,
        "schema_info": schema_info
    }

