"""Bulk seed helpers for the demo flow.

Invoke from the project root via the backend's uv environment::

    cd backend && uv run python ../scripts/demo_bulk.py add-tasks \\
        --call-id <uuid> --count 7 --thursday 2

The script talks to the same database the backend is configured for
(``settings.database_url``) using the same SQLAlchemy session factory,
so rows it writes are indistinguishable from rows the API would write.
"""

import asyncio
import random
from datetime import date, time, timedelta

import click
from sqlalchemy import select

from volunteer_call_api.database import async_session_factory
from volunteer_call_api.models import (
    Person,
    PersonRole,
    RoleType,
    Task,
    VolunteerAvailability,
    VolunteerCall,
)

ADDRESS_POOL: list[tuple[str, str]] = [
    ("1234 Oak St", "Arlington"),
    ("5678 Elm Ave", "Falls Church"),
    ("910 Maple Dr", "Vienna"),
    ("234 Pine Ln", "Fairfax"),
    ("567 Cedar Ct", "McLean"),
    ("890 Birch Way", "Annandale"),
    ("345 Walnut Rd", "Springfield"),
    ("678 Spruce Pl", "Reston"),
    ("901 Sycamore St", "Herndon"),
    ("234 Magnolia Ave", "Centreville"),
]

# Mix of long multi-task descriptions (paragraph-length, modeled on real
# RT-AFF call emails — boilerplate like "We need N volunteers to help..."
# stripped because volunteer count, city, address, and date all live in
# their own columns) and short single-task descriptions. The short ones
# exercise TaskRow's no-truncation branch; the long ones drive the
# 65-char summary + full-text-on-expand split that's the point of the
# component. Keep entries ≤500 chars to fit Task.short_description.
TASK_DESCRIPTIONS: list[str] = [
    (
        "Install three smoke/CO alarms, fire extinguisher, install five HVAC "
        "supply registers, plane sticking bathroom door, install "
        "weatherstripping and sweep on front door, repair kitchen cabinet "
        "drawer slides, install 1x6 baseboard in hall bathroom, repair "
        "corner trim on bath vanity, install lever handle on basement door, "
        "and replace handheld showerhead."
    ),
    (
        "Tune up deadbolt strikeplate, install one grab bar, install two "
        "ceiling light fixtures, replace washer hoses, and provide fire "
        "extinguisher."
    ),
    (
        "Stabilize exterior handrails, repair exterior door, weather-proof "
        "exterior outlet, clean dryer flapper, install two smoke alarms, "
        "air-seal pull-down stairs, install toilet safety rails, replace "
        "kitchen light, repair cabinet door, and install door sweep."
    ),
    (
        "AC Rescue: install two window A/C units, secure with brackets, run "
        "GFCI line check, dispose of old units, and walk homeowner through "
        "filter cleaning. Volunteers must have completed AC Rescue training."
    ),
    (
        "Replace flapper and fill valve on two toilets, install kitchen "
        "faucet, caulk around tub and vanity, secure loose shutoff valve "
        "under sink, and replace shower diverter."
    ),
    (
        "Replace four interior door knobs with lever sets, hang two new "
        "interior doors, install three smoke alarms, replace porch light, "
        "and patch and paint drywall in stairwell."
    ),
    (
        "Build and install wheelchair ramp from front walk to porch (about "
        "20 linear feet, single switchback), install grab bar in adjacent "
        "bathroom, and widen bathroom doorway hardware to lever handle."
    ),
    (
        "Repair sticking storm door closer, replace weatherstripping on "
        "front and back doors, install attic stairs insulation cover, and "
        "caulk and paint exterior trim on front-facing windows."
    ),
    "Bathroom grab-bar install",
    "Furnace filter and quick HVAC check",
    "Replace porch light fixture",
    "Roof patch and gutter cleanout",
]


@click.group()
def cli() -> None:
    """Bulk demo seeding helpers."""


def _first_monday_after(today: date) -> date:
    """First Monday *strictly* after `today` (never today itself)."""
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


def _schedule_slots(today: date) -> list[date]:
    """Two-week task schedule with variation, starting on the first Monday
    after `today`:

        Week 1: Mon, [skip Tue], Wed, Thu, Thu, Fri          (5 slots)
        Week 2: Mon, Tue, Wed, Thu, Fri, Sat                 (6 slots)

    Two Thursday slots on the first week and a Saturday on the second
    weekend are the deliberate variations. Total: 11 slots.
    """
    d0 = _first_monday_after(today)
    week1_offsets = [0, 2, 3, 3, 4]
    week2_offsets = [7, 8, 9, 10, 11, 12]
    return [d0 + timedelta(days=o) for o in week1_offsets + week2_offsets]


async def _add_tasks(call_id: str, count: int, offset: int) -> int:
    async with async_session_factory() as session:
        call = await session.get(VolunteerCall, call_id)
        if call is None:
            raise click.ClickException(f"No volunteer_call with id {call_id}")

        slots = _schedule_slots(date.today())
        if offset < 0 or offset + count > len(slots):
            raise click.ClickException(
                f"offset+count must be ≤ {len(slots)} (offset={offset}, count={count})"
            )

        rng = random.Random(call_id)
        pool = list(TASK_DESCRIPTIONS)
        rng.shuffle(pool)
        descriptions = (pool * ((count // len(pool)) + 1))[:count]

        for i in range(count):
            d = slots[offset + i]
            address, city = rng.choice(ADDRESS_POOL)
            session.add(
                Task(
                    volunteer_call_id=call_id,
                    short_description=descriptions[i],
                    date=d,
                    time_start=time(9, 0),
                    time_end=time(15, 0),
                    address=address,
                    city=city,
                    volunteers_needed=rng.choice([3, 4, 4, 5]),
                    skilled_needed=rng.choice([0, 0, 1]),
                )
            )

        await session.commit()
        return count


async def _respond_availability(call_id: str, count: int) -> int:
    async with async_session_factory() as session:
        call = await session.get(VolunteerCall, call_id)
        if call is None:
            raise click.ClickException(f"No volunteer_call with id {call_id}")

        tasks_rows = await session.execute(
            select(Task).where(Task.volunteer_call_id == call_id)
        )
        tasks: list[Task] = list(tasks_rows.scalars().all())
        if not tasks:
            raise click.ClickException(f"Call {call_id} has no tasks yet")

        already = await session.execute(
            select(VolunteerAvailability.person_id)
            .where(VolunteerAvailability.volunteer_call_id == call_id)
            .distinct()
        )
        excluded = {row[0] for row in already}

        # Volunteer-only: exclude anyone who also has a staff or
        # team_leader role. Real RT-AFF team leads coordinate from the
        # admin side and don't typically submit availability through the
        # same flow, so the demo dataset should reflect that.
        admin_role_subq = select(PersonRole.person_id).where(
            PersonRole.role.in_([RoleType.STAFF, RoleType.TEAM_LEADER])
        )
        candidates_rows = await session.execute(
            select(Person)
            .join(PersonRole, PersonRole.person_id == Person.id)
            .where(PersonRole.role == RoleType.VOLUNTEER)
            .where(Person.active.is_(True))
            .where(Person.id.notin_(admin_role_subq))
        )
        candidates = [p for p in candidates_rows.scalars().unique().all() if p.id not in excluded]

        rng = random.Random(call_id + "|availability")
        rng.shuffle(candidates)
        picks = candidates[:count]
        if len(picks) < count:
            raise click.ClickException(
                f"Only {len(picks)} eligible volunteers (requested {count})."
            )

        n_tasks = len(tasks)
        for person in picks:
            # Realistic respondent: each volunteer picks 1–4 tasks
            pick_count = min(n_tasks, rng.choices([1, 2, 3, 4], weights=[2, 3, 4, 3])[0])
            subset = rng.sample(tasks, pick_count)
            for task in subset:
                session.add(
                    VolunteerAvailability(
                        volunteer_call_id=call_id,
                        person_id=person.id,
                        task_id=task.id,
                        available=True,
                    )
                )

        await session.commit()
        return len(picks)


@cli.command("add-tasks")
@click.option("--call-id", required=True, help="VolunteerCall.id to add tasks under")
@click.option("--count", type=int, default=9, show_default=True)
@click.option(
    "--offset",
    type=int,
    default=0,
    show_default=True,
    help=(
        "Start index in the 11-slot two-week schedule "
        "(Mon, Wed, Thu×2, Fri, Mon, Tue, Wed, Thu, Fri, Sat). "
        "Use a non-zero offset when tasks at slots 0..offset-1 are added by hand."
    ),
)
def add_tasks_cmd(call_id: str, count: int, offset: int) -> None:
    """Add COUNT synthetic tasks to an existing call, filling consecutive
    slots of the two-week schedule starting from --offset."""
    inserted = asyncio.run(_add_tasks(call_id, count, offset))
    click.echo(f"Inserted {inserted} task(s) into call {call_id}.")


@cli.command("respond-availability")
@click.option("--call-id", required=True, help="VolunteerCall.id to respond against")
@click.option("--count", type=int, default=23, show_default=True)
def respond_availability_cmd(call_id: str, count: int) -> None:
    """Have COUNT random volunteer-only people (no staff / team-leads)
    submit availability for the call. Each picks 1–3 tasks (weights
    3-4-3), matching realistic respondent behavior — the demo's one
    "signs up for everything" volunteer is driven separately."""
    responded = asyncio.run(_respond_availability(call_id, count))
    click.echo(f"{responded} volunteer(s) responded to call {call_id}.")


if __name__ == "__main__":
    cli()
