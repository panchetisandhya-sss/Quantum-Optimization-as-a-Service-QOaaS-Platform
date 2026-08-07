import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# Helper for UUID representation across SQLite and PostgreSQL
def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="business_analyst")
    created_at = Column(DateTime, default=datetime.utcnow)

class OptimizationJob(Base):
    __tablename__ = "optimization_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    service_type = Column(String(50), nullable=False)  # "portfolio" or "staffing"
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED, TIMED_OUT
    input_data = Column(JSON, nullable=True)  # Stores parsed asset or employee list
    results = Column(JSON, nullable=True)     # Stores optimization details, weights, metric calculations
    ai_explanation = Column(Text, nullable=True)
    encrypted_pdf_path = Column(String(555), nullable=True)
    encryption_key = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # "qubo", "algorithm", "circuit", "documentation", "code", "research"
    description = Column(Text, nullable=False)
    markdown_content = Column(Text, nullable=True)
    code_content = Column(Text, nullable=True)
    file_path = Column(String(555), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)


class OrgBackendConfig(Base):
    """
    Per-user quantum hardware backend configuration.
    API tokens are stored AES-256-GCM encrypted at rest via core/security.py.
    Tokens are NEVER logged or returned in plaintext.
    """
    __tablename__ = "org_backend_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    # Provider: "ibm" | "dwave" | "braket" | "local"
    provider = Column(String(50), nullable=False, default="local")
    # Encrypted API token (AES-256-GCM ciphertext hex + nonce + tag)
    encrypted_api_token = Column(Text, nullable=True)
    # Optional: backend endpoint URL (e.g. IBM instance URL)
    endpoint_url = Column(String(512), nullable=True)
    # Optional: specific backend/device name (e.g. "ibm_brisbane")
    backend_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
