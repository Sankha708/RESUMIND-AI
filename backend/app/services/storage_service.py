"""Isolated Ephemeral Storage Service.

Manages isolated per-session directories under:
- storage/uploads/{session_id}/
- storage/exports/{session_id}/
- storage/reports/{session_id}/

Strictly enforces directory containment and path-traversal prevention.
"""

import re
import shutil
from pathlib import Path
from typing import Dict
from app.config import settings

# Strict UUID/safe identifier regex pattern
SAFE_SESSION_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{8,64}$")


class StorageSecurityError(ValueError):
    """Raised when an invalid or unsafe session identifier is supplied."""
    pass


def get_base_storage_paths(base_root: Path | None = None) -> Dict[str, Path]:
    """Returns the absolute root directories for uploads, exports, and reports."""
    root = (base_root or settings.storage_path).resolve()
    return {
        "uploads": root / "uploads",
        "exports": root / "exports",
        "reports": root / "reports",
    }


def validate_session_id(session_id: str) -> str:
    """Validates that a session_id adheres strictly to safe character constraints."""
    if not session_id or not SAFE_SESSION_ID_PATTERN.match(session_id):
        raise StorageSecurityError(f"Unsafe session identifier rejected: '{session_id}'")
    return session_id


def get_session_storage_dirs(
    session_id: str, base_root: Path | None = None
) -> Dict[str, Path]:
    """Resolves isolated storage directories for a validated session identifier."""
    valid_id = validate_session_id(session_id)
    roots = get_base_storage_paths(base_root)

    dirs = {}
    for category, root in roots.items():
        session_dir = (root / valid_id).resolve()
        # Verify the resolved directory stays strictly inside the category root
        if not session_dir.is_relative_to(root):
            raise StorageSecurityError(
                f"Path traversal detected: {session_dir} is outside {root}"
            )
        dirs[category] = session_dir

    return dirs


def ensure_session_storage(
    session_id: str, base_root: Path | None = None
) -> Dict[str, Path]:
    """Creates the isolated storage directories for a session with safe permissions."""
    dirs = get_session_storage_dirs(session_id, base_root)
    for category_dir in dirs.values():
        category_dir.mkdir(parents=True, exist_ok=True)
    return dirs


def delete_session_storage(
    session_id: str, base_root: Path | None = None
) -> None:
    """Safely and idempotently removes all storage directories for a session."""
    dirs = get_session_storage_dirs(session_id, base_root)
    for category, category_dir in dirs.items():
        try:
            if category_dir.exists() and category_dir.is_dir():
                shutil.rmtree(category_dir, ignore_errors=True)
        except Exception:
            # Idempotent cleanup: ignore errors if already deleted or inaccessible
            pass
