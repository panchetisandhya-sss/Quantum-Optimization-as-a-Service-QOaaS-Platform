"""
services/qrng.py — Phase 4: Real Quantum Random Number Generation + QR code generation.

Functions:
  get_quantum_random_bytes(n_bytes) → (bytes, source_label)
    Tries the ANU QRNG API first, falls back to a local Qiskit Hadamard circuit.

  generate_verification_token(job_id, entropy_bytes) → str
    HMAC-SHA256 of job_id + quantum entropy → URL-safe token.

  generate_qr_code(data_string) → bytes
    PNG QR code image for use in PDF reports and frontend display.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import os
from typing import Optional, Tuple

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import qrcode library (optional)
HAS_QRCODE = False
try:
    import qrcode  # type: ignore
    from qrcode.image.pure import PyPNGImage  # type: ignore
    HAS_QRCODE = True
except ImportError:
    logger.warning(
        "qrcode[pil] not installed. QR code generation will be unavailable. "
        "Install with: pip install 'qrcode[pil]'"
    )

# Try to import Qiskit for local QRNG fallback
HAS_QISKIT_QRNG = False
try:
    from qiskit import QuantumCircuit  # type: ignore
    from qiskit_aer import AerSimulator  # type: ignore
    HAS_QISKIT_QRNG = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Quantum Random Bytes
# ---------------------------------------------------------------------------

def get_quantum_random_bytes(n_bytes: int) -> Tuple[bytes, str]:
    """
    Retrieve n_bytes of quantum-true random data.

    Priority:
      1. ANU Quantum Random Number Generator API (unauthenticated, free)
         Endpoint: https://qrng.anu.edu.au/API/jsonI.php?length=N&type=uint8
      2. Local Qiskit Hadamard circuit (Aer simulator fallback)
      3. os.urandom() (last resort — classical PRNG, labelled accordingly)

    Returns:
        (random_bytes, source_label)
    """
    # Attempt 1: ANU QRNG API
    anu_bytes, anu_err = _try_anu_qrng(n_bytes)
    if anu_bytes is not None:
        return anu_bytes, "ANU Quantum Random Number Generator (API)"

    logger.warning(f"ANU QRNG unavailable: {anu_err}. Trying local Qiskit circuit.")

    # Attempt 2: Local Qiskit Hadamard
    if HAS_QISKIT_QRNG:
        qiskit_bytes, qiskit_err = _try_qiskit_qrng(n_bytes)
        if qiskit_bytes is not None:
            return qiskit_bytes, "Local Qiskit Hadamard Circuit (QRNG Fallback)"
        logger.warning(f"Qiskit QRNG failed: {qiskit_err}. Falling back to os.urandom().")

    # Attempt 3: Classical OS entropy
    logger.warning("Using os.urandom() — classical PRNG, not a quantum source.")
    return os.urandom(n_bytes), "os.urandom() Classical Fallback (No Quantum Source Available)"


def _try_anu_qrng(n_bytes: int) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Fetch random uint8 values from the ANU QRNG REST API.
    Max request: 1024 values per call — we make multiple calls if needed.
    """
    ANU_MAX_PER_CALL = 1024
    collected: list = []
    try:
        remaining = n_bytes
        while remaining > 0:
            length = min(remaining, ANU_MAX_PER_CALL)
            url = f"{settings.QRNG_ANU_URL}?length={length}&type=uint8"
            resp = requests.get(url, timeout=settings.QRNG_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                return None, f"ANU API returned success=false: {data}"
            collected.extend(data["data"])
            remaining -= length

        return bytes(collected[:n_bytes]), None
    except Exception as exc:
        return None, str(exc)


def _try_qiskit_qrng(n_bytes: int) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate random bytes using a Qiskit QuantumCircuit with Hadamard gates.
    Each circuit produces n_bits bits; we run ceil(n_bytes * 8 / n_bits) shots.
    """
    try:
        n_bits_per_circuit = 16  # 16-qubit Hadamard circuit
        n_circuits = math.ceil((n_bytes * 8) / n_bits_per_circuit)

        qc = QuantumCircuit(n_bits_per_circuit, n_bits_per_circuit)
        for i in range(n_bits_per_circuit):
            qc.h(i)
        qc.measure_all()

        # Remove the auto-added barrier-based measure_all and use manual
        qc = QuantumCircuit(n_bits_per_circuit)
        qc.h(range(n_bits_per_circuit))
        qc.measure_all()

        sim = AerSimulator()
        from qiskit import transpile
        compiled = transpile(qc, sim)
        job = sim.run(compiled, shots=n_circuits, memory=True)
        result = job.result()
        memory = result.get_memory()  # list of bitstrings e.g. ['0110...', ...]

        all_bits = "".join(memory)
        needed_bits = n_bytes * 8
        if len(all_bits) < needed_bits:
            return None, "Insufficient bits from Qiskit circuit."

        # Convert bit string to bytes
        raw_bytes = int(all_bits[:needed_bits], 2).to_bytes(n_bytes, byteorder="big")
        return raw_bytes, None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Verification Token
# ---------------------------------------------------------------------------

def generate_verification_token(job_id: str, entropy_bytes: bytes) -> str:
    """
    Generate a URL-safe HMAC-SHA256 verification token for a job.

    The token is a hex digest of HMAC(SECRET_KEY, job_id + entropy_bytes).
    This allows the /verify endpoint to confirm token authenticity without
    storing it as plaintext in the database.

    Returns a 64-character hex string.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    message = job_id.encode("utf-8") + entropy_bytes
    token = hmac.new(key, message, hashlib.sha256).hexdigest()
    return token


# ---------------------------------------------------------------------------
# QR Code Generation
# ---------------------------------------------------------------------------

def generate_qr_code(data_string: str, box_size: int = 6) -> Optional[bytes]:
    """
    Generate a PNG QR code image encoding data_string.

    Returns PNG bytes, or None if qrcode library is not installed.
    """
    if not HAS_QRCODE:
        logger.warning("qrcode library not available. Skipping QR code generation.")
        return None

    import io
    qr = qrcode.QRCode(
        version=None,            # auto-detect minimum size
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=2,
    )
    qr.add_data(data_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
