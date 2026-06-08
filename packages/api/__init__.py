"""
CivicOS API — package root. Re-exports commonly used symbols.
"""

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
