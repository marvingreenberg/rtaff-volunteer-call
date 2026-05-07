"""Tests for asyncpg URL normalization."""

from volunteer_call_api.db_url import normalize_async_url


def test_strips_sslmode_require_and_sets_ssl_true() -> None:
    url, connect_args = normalize_async_url(
        "postgresql+asyncpg://user:pw@host:5432/db?sslmode=require"
    )
    assert "sslmode" not in url.query
    assert connect_args == {"ssl": True}


def test_sslmode_disable_sets_ssl_false() -> None:
    _, connect_args = normalize_async_url("postgresql+asyncpg://user:pw@host/db?sslmode=disable")
    assert connect_args == {"ssl": False}


def test_sslmode_prefer_omits_ssl_arg() -> None:
    # asyncpg has no equivalent for libpq's "prefer"; we drop the param
    # rather than guess. asyncpg's default already negotiates TLS when
    # the server offers it.
    url, connect_args = normalize_async_url("postgresql+asyncpg://user:pw@host/db?sslmode=prefer")
    assert "sslmode" not in url.query
    assert "ssl" not in connect_args


def test_strips_other_libpq_only_params() -> None:
    url, _ = normalize_async_url(
        "postgresql+asyncpg://user:pw@host/db"
        "?sslmode=require&channel_binding=require&sslrootcert=/etc/ca.pem"
    )
    assert "channel_binding" not in url.query
    assert "sslrootcert" not in url.query


def test_preserves_unrelated_query_params() -> None:
    url, _ = normalize_async_url(
        "postgresql+asyncpg://user:pw@host/db?sslmode=require&application_name=volunteer_call"
    )
    assert url.query.get("application_name") == "volunteer_call"


def test_no_query_params_is_passthrough() -> None:
    url, connect_args = normalize_async_url(
        "postgresql+asyncpg://volunteer_call:volunteer_call_dev@localhost:5432/volunteer_call"
    )
    assert url.query == {}
    assert connect_args == {}
    assert url.host == "localhost"
    assert url.database == "volunteer_call"
