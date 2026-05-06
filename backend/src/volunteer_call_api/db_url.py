"""Database URL normalization for asyncpg.

asyncpg does not accept libpq-style query params like ``sslmode`` or
``channel_binding`` that commonly appear in managed Postgres connection
strings (Cloud SQL, Supabase, Neon, etc.). This module strips those params
from the URL and translates them into asyncpg ``connect_args``.
"""

from typing import Any

from sqlalchemy.engine.url import URL, make_url

LIBPQ_SSL_REQUIRED_MODES = frozenset({"require", "verify-ca", "verify-full"})
LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding", "sslrootcert", "sslcert", "sslkey")


def normalize_async_url(raw_url: str) -> tuple[URL, dict[str, Any]]:
    """Return an asyncpg-compatible URL and connect_args.

    Strips libpq-only query params from the URL and converts ``sslmode``
    to an ``ssl`` connect arg understood by asyncpg.
    """
    url = make_url(raw_url)
    query = dict(url.query)
    connect_args: dict[str, Any] = {}

    sslmode = query.pop("sslmode", None)
    if sslmode in LIBPQ_SSL_REQUIRED_MODES:
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False

    for key in LIBPQ_ONLY_PARAMS:
        query.pop(key, None)

    return url.set(query=query), connect_args
