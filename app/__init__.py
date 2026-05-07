from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version


def _read_version() -> str:
    try:
        return _pkg_version("python-agent-boilerplate")
    except PackageNotFoundError:
        # Fallback when running from a raw source tree (no installed dist-info).
        import tomllib
        from pathlib import Path

        try:
            pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
            return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
        except FileNotFoundError, KeyError, tomllib.TOMLDecodeError:
            return "0.0.0+unknown"


__version__ = _read_version()

__all__ = ["__version__"]
