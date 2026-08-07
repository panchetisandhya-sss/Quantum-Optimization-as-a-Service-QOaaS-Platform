import os
import sys
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Quantum Optimization-as-a-Service (QOaaS) Platform"
    API_V1_STR: str = "/api/v1"

    # Deployment environment: "development" | "production"
    # In production, missing required secrets cause a startup failure.
    ENV: str = os.getenv("ENV", "development")

    # JWT secret — must be set via environment variable in production.
    # In development a default is allowed so the stack starts with zero config.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "quantum_secure_super_secret_key_1337_2026")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./qoaas.db")

    # OpenAI (optional — fallback template used when not set)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # SMTP — password must be set via env; default allowed in development only
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "admin@qoaas-platform.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@qoaas-platform.com")
    EMAILS_FROM_NAME: str = "Enterprise QOaaS Platform"

    # IBM Quantum (optional)
    IBMQ_TOKEN: str = os.getenv("IBMQ_TOKEN", "")

    # CORS — comma-separated list of allowed origins.
    # Override with ALLOWED_ORIGINS or CORS_ORIGINS env variable in production.
    CORS_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        os.getenv("CORS_ORIGINS", "http://localhost:3000")
    )

    # Admin allow-list — comma-separated email addresses that receive the
    # "administrator" role on registration. Empty means no auto-admins.
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")

    # Internationalisation defaults (per-org overrides come from job input_data)
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "USD")
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    # QRNG — ANU Quantum Random Number Generator endpoint
    QRNG_ANU_URL: str = "https://qrng.anu.edu.au/API/jsonI.php"
    QRNG_TIMEOUT_SECONDS: int = 5

    class Config:
        case_sensitive = True

    def get_cors_origins(self) -> list:
        """Parse the CORS_ORIGINS string into a list of stripped origin strings."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def get_admin_emails(self) -> set:
        """Parse the ADMIN_EMAILS string into a set of lower-cased email addresses."""
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}


settings = Settings()

# ── Fail-fast secret validation (production only) ──────────────────────────
if settings.ENV == "production":
    _REQUIRED = {
        "SECRET_KEY": settings.SECRET_KEY,
        "SMTP_PASSWORD": settings.SMTP_PASSWORD,
    }
    _DEFAULTS = {
        "SECRET_KEY": "quantum_secure_super_secret_key_1337_2026",
        "SMTP_PASSWORD": "",
    }
    missing = []
    for name, val in _REQUIRED.items():
        if not val or val == _DEFAULTS.get(name):
            missing.append(name)
    if missing:
        print(
            f"[QOaaS FATAL] Running in production but required secrets are unset "
            f"or use insecure defaults: {missing}. Set them via environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)
