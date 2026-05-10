"""Shared Jinja environment for email templates with the theme preloaded."""

from jinja2 import Environment, PackageLoader, select_autoescape

from volunteer_call_api.services.email_theme import load_theme

jinja_env = Environment(
    loader=PackageLoader("volunteer_call_api", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
jinja_env.globals["theme"] = load_theme()
