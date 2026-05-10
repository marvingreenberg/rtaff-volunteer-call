"""Tests for theme loading and theme-driven template rendering."""

from volunteer_call_api.services.email_render import jinja_env
from volunteer_call_api.services.email_theme import load_theme


def test_load_theme_has_required_sections() -> None:
    """The shipped theme file must define every section the templates read.
    A missing section would raise UndefinedError at email-send time, after
    the template starts rendering — well past the API request boundary."""
    theme = load_theme()
    assert set(theme["brand"]) >= {"name", "short_name"}
    assert set(theme["colors"]) >= {
        "page_background",
        "card_background",
        "primary",
        "primary_dark",
        "body_text",
        "muted_text",
        "highlight",
    }
    assert isinstance(theme["footer"]["lines"], list)


def test_jinja_env_has_theme_global() -> None:
    """The shared env must expose `theme` to every template, otherwise
    `{{ theme.colors.primary }}` would render as empty and the email loses
    all its color."""
    assert "theme" in jinja_env.globals
    assert jinja_env.globals["theme"]["brand"]["short_name"] == "RT-AFF"


def test_magic_link_template_uses_theme_color_for_button() -> None:
    """The login email's CTA button must be styled with the theme's primary
    color — catches a regression where a child template hard-codes a hex
    value and stops responding to theme edits."""
    theme = load_theme()
    template = jinja_env.get_template("magic_link_login.html")
    html = template.render(
        subject="Log in",
        title="Log in to RT-AFF",
        subtitle=None,
        first_name="Sam",
        login_url="https://app.example.com/verify?token=abc",
    )
    assert theme["colors"]["primary"] in html
    assert theme["colors"]["highlight"] in html
    assert 'href="https://app.example.com/verify?token=abc"' in html


def test_base_template_renders_footer_lines_from_theme() -> None:
    """Footer copy should come from the theme so a non-coder edits one TOML
    file instead of touching every template."""
    theme = load_theme()
    template = jinja_env.get_template("magic_link_login.html")
    html = template.render(
        subject="Log in",
        title="Log in",
        subtitle=None,
        first_name="Sam",
        login_url="https://x/y",
    )
    for line in theme["footer"]["lines"]:
        assert line in html


def test_theme_change_propagates_to_templates() -> None:
    """If we mutate the theme global, the next render reflects it. This is
    what proves the theme is actually wired in (not silently shadowed by a
    template-level default), and is how a future dynamic-theme feature would
    plug in."""
    original = jinja_env.globals["theme"]
    try:
        custom = {
            "brand": {"name": "Test Org", "short_name": "TST"},
            "colors": {
                "page_background": "#000001",
                "card_background": "#000002",
                "primary": "#abcdef",
                "primary_dark": "#000003",
                "body_text": "#000004",
                "muted_text": "#000005",
                "highlight": "#fedcba",
            },
            "footer": {"lines": ["Custom footer line"]},
        }
        jinja_env.globals["theme"] = custom
        html = jinja_env.get_template("magic_link_login.html").render(
            subject="x",
            title="x",
            subtitle=None,
            first_name="Sam",
            login_url="https://x/y",
        )
        assert "#abcdef" in html
        assert "#fedcba" in html
        assert "Custom footer line" in html
    finally:
        jinja_env.globals["theme"] = original
