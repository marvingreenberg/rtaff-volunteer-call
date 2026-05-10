# Email templates

These files control everything that gets sent by email — login links,
volunteer call invitations, assignment notices, and thank-you notes.

There are three layers, ordered from "easiest to edit" to "biggest commitment":

## 1. `email_theme.toml` — colors, name, footer copy

Edit this file to change brand colors, organization name, or footer lines
across **every** email at once. Plain text, no HTML or code knowledge needed.
Restart the API for changes to take effect (the file is read once at startup).

Example — changing the primary brand color:

```toml
[colors]
primary = "#7dc242"  # change this hex value to recolor buttons + accent stripe
```

## 2. `assets/` — logo and accent images

Replace `rtaff-logo.png` and `tools-image.jpg` with your own. Keep the
filenames the same. Recommended sizes:

- `rtaff-logo.png` — about 700 × 220 px, transparent background
- `tools-image.jpg` — about 800 × 211 px, full-width banner

Images are embedded inline in the email (CID), so they show up even when the
recipient's mail client blocks remote images.

## 3. The HTML templates — body copy and layout

Each email kind has its own template:

| Template                       | When it's sent                                |
| ------------------------------ | --------------------------------------------- |
| `magic_link_login.html`        | Someone clicks "Email me a login link"        |
| `volunteer_invite.html`        | Admin sends a volunteer call to the program   |
| `volunteer_assignment.html`    | Admin sends out finalized team assignments    |
| `volunteer_thanks.html`        | Same step, but for volunteers not assigned    |

All four extend `email_base.html`, which is the shared shell (logo, tools
strip, title band, footer). Editing the shell changes every email; editing
one of the four child templates only changes that one.

The templates use [Jinja2](https://jinja.palletsprojects.com/) syntax —
`{{ variable }}` interpolates a value, `{% if %}` / `{% for %}` are
conditionals and loops. The variables available to each template are listed
at the top of `services/notifications.py` and `routes/auth.py`.

### Theme variables inside templates

Anywhere in a template you can reference the theme:

- `{{ theme.brand.name }}`, `{{ theme.brand.short_name }}`
- `{{ theme.colors.primary }}`, `{{ theme.colors.highlight }}`, etc.
- `{% for line in theme.footer.lines %}…{% endfor %}`

This means if you change `email_theme.toml`, every template that uses
`{{ theme.* }}` picks the change up automatically.

## Previewing changes

Start the dev stack (`make dev`) and trigger the email — Mailpit at
http://localhost:8025 will show the rendered result, including images.
