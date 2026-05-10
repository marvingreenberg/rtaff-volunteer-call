"""Loader for the editable email theme (templates/email_theme.toml)."""

import tomllib
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def load_theme() -> dict[str, Any]:
    """Read and cache templates/email_theme.toml.

    Cached for the process lifetime; restart the API to pick up edits.
    """
    raw = (files("volunteer_call_api.templates") / "email_theme.toml").read_bytes()
    return tomllib.loads(raw.decode("utf-8"))
