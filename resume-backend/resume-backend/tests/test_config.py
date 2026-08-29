"""Settings must accept the documented .env format."""

from __future__ import annotations

import pathlib


def test_comma_separated_cors_origins_parse_from_dotenv(tmp_path: pathlib.Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n"
        "SECRET_KEY=test-secret-key-32-bytes-minimum-xxxx\n"
    )
    from app.config import Settings

    settings = Settings(_env_file=str(env_file))
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
