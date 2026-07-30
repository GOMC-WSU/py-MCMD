"""Authoritative py-MCMD framework version."""

__version__ = "2.1.0"


def get_version() -> str:
    """Return the authoritative py-MCMD framework version string."""
    return __version__


__all__ = ["__version__", "get_version"]
