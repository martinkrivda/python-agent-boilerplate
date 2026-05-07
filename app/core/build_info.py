from __future__ import annotations

from pydantic import BaseModel

from app.core.config import Settings


class BuildInfo(BaseModel):
    """Provenance of the running build.

    Populated from environment variables at startup (typically baked at Docker
    build time). Both fields default to "" so local development from a source
    tree shows no build metadata rather than misleading values.
    """

    commit: str = ""
    timestamp: str = ""

    @classmethod
    def from_settings(cls, settings: Settings) -> BuildInfo:
        return cls(
            commit=settings.build_commit,
            timestamp=settings.build_timestamp,
        )
