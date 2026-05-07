import tomllib
from pathlib import Path


def _read_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    except FileNotFoundError, KeyError, tomllib.TOMLDecodeError:
        return "0.0.0+unknown"


__version__ = _read_version()

__all__ = ["__version__"]
