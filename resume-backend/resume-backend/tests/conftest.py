"""Test environment: isolated DB and stable settings, set before any app import."""

import os
import pathlib

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_pytest.db")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-32-bytes-minimum-xx")
os.environ.setdefault("DEBUG", "false")
# Individual tests opt back in with tiny limits; everything else runs unthrottled.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

pathlib.Path("test_pytest.db").unlink(missing_ok=True)
