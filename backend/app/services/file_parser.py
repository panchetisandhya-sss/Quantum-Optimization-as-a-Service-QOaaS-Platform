"""
services/file_parser.py — Phase 3: CSV/PDF bulk employee roster parser.

Parses uploaded CSV or PDF files into the employee list format expected by
modeling.py's parse_and_model_staffing().

Required CSV columns (case-insensitive):
  name         — employee full name
  hourly_rate  — numeric, e.g. 25.50
  availability — comma-separated shift IDs, e.g. "shift_1,shift_2"
  skills       — comma-separated skill tags, e.g. "support,billing"

Returns a tuple:
  (employees: list[dict], errors: list[dict])

Errors are always actionable — they name the row and the specific field.
Malformed rows are never silently dropped.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Try to import pdfplumber (optional — only needed for PDF uploads)
HAS_PDFPLUMBER = False
try:
    import pdfplumber  # type: ignore
    HAS_PDFPLUMBER = True
except ImportError:
    logger.warning(
        "pdfplumber not installed. PDF upload parsing will be unavailable. "
        "Install with: pip install pdfplumber"
    )

# Canonical column names (lower-cased)
REQUIRED_COLUMNS = {"name", "hourly_rate", "availability", "skills"}

# Maximum file size: 50 MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def parse_csv_employees(
    file_bytes: bytes,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse a CSV byte string into a list of employee dicts.

    Returns:
        employees: list of valid employee dicts
        errors:    list of {"row": int, "field": str, "issue": str}
    """
    employees: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    try:
        text = file_bytes.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception as exc:
            return [], [{"row": 0, "field": "file", "issue": f"Cannot decode file: {exc}"}]

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], [{"row": 0, "field": "file", "issue": "File is empty or has no header row."}]

    # Normalise header names
    raw_headers = [h.strip().lower() for h in reader.fieldnames]
    normalised_headers = set(raw_headers)

    # Required field groups (at least one header from each group must be present)
    has_name = any(k in normalised_headers for k in ["name", "employee_name", "employee name", "emp_name"])
    has_gender = any(k in normalised_headers for k in ["gender", "sex"])
    has_address = any(k in normalised_headers for k in ["address", "zone", "location", "city", "pincode", "zip"])
    has_health = any(k in normalised_headers for k in ["health_condition", "health_status", "health", "medical_status"])

    missing_groups = []
    if not has_name:
        missing_groups.append("name (or employee_name)")
    if not has_gender:
        missing_groups.append("gender (or sex)")
    if not has_address:
        missing_groups.append("address (or zone/city/pincode)")
    if not has_health:
        missing_groups.append("health_condition (or health_status)")

    if missing_groups:
        return [], [
            {
                "row": 0,
                "field": ", ".join(missing_groups),
                "issue": f"Required columns missing: {', '.join(missing_groups)}. Found headers: {', '.join(reader.fieldnames)}.",
            }
        ]

    for row_num, raw_row in enumerate(reader, start=2):  # row 1 = header
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        # Employee ID & Name
        emp_id = row.get("employee_id") or row.get("id") or row.get("emp_id") or f"emp_{row_num-1}"
        name = row.get("name") or row.get("employee_name") or row.get("employee name") or row.get("emp_name", "").strip()
        if not name:
            errors.append({"row": row_num, "field": "name", "issue": "Employee name is empty."})
            continue

        # Gender validation
        gender_raw = row.get("gender") or row.get("sex", "").strip()
        if not gender_raw:
            errors.append({"row": row_num, "field": "gender", "issue": "Gender field is empty."})
            continue
        gender = "Female" if gender_raw.lower().startswith("f") or gender_raw.lower().startswith("woman") else "Male"

        # Address / Zone validation
        address_raw = row.get("address") or row.get("zone") or row.get("location") or row.get("zip") or row.get("city") or row.get("pincode", "").strip()
        if not address_raw:
            errors.append({"row": row_num, "field": "address", "issue": "Address/Zone field is empty."})
            continue

        # Health Condition validation
        health_raw = row.get("health_condition") or row.get("health_status") or row.get("health") or row.get("medical_status", "").strip()
        if not health_raw:
            errors.append({"row": row_num, "field": "health_condition", "issue": "Health condition field is empty."})
            continue

        # hourly_rate (optional, default 25.0)
        hourly_rate = 25.0
        if row.get("hourly_rate") or row.get("rate") or row.get("cost"):
            rate_str = row.get("hourly_rate") or row.get("rate") or row.get("cost")
            try:
                hourly_rate = float(rate_str.replace(",", ""))
                if hourly_rate < 0:
                    raise ValueError("negative")
            except ValueError:
                errors.append({"row": row_num, "field": "hourly_rate", "issue": f"Not a valid rate: {repr(rate_str)}."})
                continue

        # availability & skills (optional)
        avail_raw = row.get("availability") or row.get("shift_preference") or row.get("shifts") or row.get("preferred_shift", "")
        availability = [s.strip() for s in avail_raw.split(",") if s.strip()]

        skills_raw = row.get("skills", "")
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()] or ["general"]

        employees.append(
            {
                "id": emp_id,
                "name": name,
                "hourly_rate": hourly_rate,
                "availability": availability,
                "skills": skills,
                "gender": gender,
                "address": address_raw,
                "health_condition": health_raw,
            }
        )

    return employees, errors


def parse_pdf_employees(
    file_bytes: bytes,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract a tabular employee roster from a PDF file and parse it as CSV.

    Strategy:
      1. Use pdfplumber to extract tables from all pages.
      2. Concatenate all table rows into a CSV-like structure.
      3. Delegate to parse_csv_employees() for validation.
    """
    if not HAS_PDFPLUMBER:
        return [], [
            {
                "row": 0,
                "field": "file",
                "issue": "PDF parsing is not available. Please install pdfplumber or upload a CSV file.",
            }
        ]

    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as exc:
        return [], [{"row": 0, "field": "file", "issue": f"Could not open PDF: {exc}"}]

    all_rows: List[List[str]] = []
    header_found = False

    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            for row in table:
                # Clean cells
                cleaned = [(cell or "").strip() for cell in row]
                if not header_found:
                    # Check if this row looks like the header
                    lower_row = [c.lower() for c in cleaned]
                    if any(col in lower_row for col in REQUIRED_COLUMNS):
                        header_found = True
                all_rows.append(cleaned)

    pdf.close()

    if not all_rows:
        return [], [
            {
                "row": 0,
                "field": "file",
                "issue": "No tables found in the PDF. Please ensure your PDF contains a data table "
                         "with columns: name, hourly_rate, availability, skills.",
            }
        ]

    # Convert to CSV bytes and re-use the CSV parser
    output = io.StringIO()
    writer = csv.writer(output)
    for row in all_rows:
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")
    return parse_csv_employees(csv_bytes)


def parse_employee_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Route to the correct parser based on the file extension.

    Args:
        file_bytes: raw file content
        filename:   original filename (used to detect format)

    Returns:
        (employees, errors) — same as parse_csv_employees / parse_pdf_employees
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return [], [
            {
                "row": 0,
                "field": "file",
                "issue": f"File too large ({len(file_bytes) // (1024*1024)} MB). Maximum allowed is 50 MB.",
            }
        ]

    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        return parse_csv_employees(file_bytes)
    elif lower_name.endswith(".pdf"):
        return parse_pdf_employees(file_bytes)
    else:
        return [], [
            {
                "row": 0,
                "field": "file",
                "issue": f"Unsupported file type '{filename}'. Please upload a .csv or .pdf file.",
            }
        ]
