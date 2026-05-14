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

TASK_DESCRIPTIONS: list[str] = [
    "Kitchen cabinet replacement",
    "Bathroom grab-bar install",
    "Deck repair and staining",
    "Roof patch + gutter cleanup",
    "Wheelchair ramp construction",
    "Furnace filter + HVAC inspection",
    "Exterior painting (single story)",
    "Front door + storm door replacement",
    "Floor refinishing — living room",
    "Garage cleanout and reorganize",
    "Window seal + weatherproofing",
    "Plumbing fixture replacement",
]


@click.group()
def cli() -> None:
    """Bulk demo seeding helpers."""


async def _add_tasks(call_id: str, count: int, thursday: int) -> int:
    async with async_session_factory() as session:
        call = await session.get(VolunteerCall, call_id)
        if call is None:
            raise click.ClickException(f"No volunteer_call with id {call_id}")

        today = date.today()
        days_to_thursday = (3 - today.weekday()) % 7 or 7
        thursday_date = today + timedelta(days=days_to_thursday)
        weekend_dates = [thursday_date + timedelta(days=i) for i in (1, 2, 3)]

        rng = random.Random(call_id)
        pool = list(TASK_DESCRIPTIONS)
        rng.shuffle(pool)
        descriptions = (pool * ((count // len(pool)) + 1))[:count]

        for i in range(count):
            d = thursday_date if i < thursday else rng.choice(weekend_dates)
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

        candidates_rows = await session.execute(
            select(Person)
            .join(PersonRole, PersonRole.person_id == Person.id)
            .where(PersonRole.role == RoleType.VOLUNTEER)
            .where(Person.active.is_(True))
        )
        candidates = [p for p in candidates_rows.scalars().unique().all() if p.id not in excluded]

        rng = random.Random(call_id + "|availability")
        rng.shuffle(candidates)
        picks = candidates[:count]
        if len(picks) < count:
            raise click.ClickException(
                f"Only {len(picks)} eligible volunteers (requested {count})."
            )

        for person in picks:
            subset = rng.sample(tasks, rng.randint(1, len(tasks)))
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
@click.option("--count", type=int, default=7, show_default=True)
@click.option(
    "--thursday",
    type=int,
    default=0,
    show_default=True,
    help="How many of the tasks should land on the next Thursday (rest go weekend).",
)
def add_tasks_cmd(call_id: str, count: int, thursday: int) -> None:
    """Add COUNT synthetic tasks to an existing call."""
    inserted = asyncio.run(_add_tasks(call_id, count, thursday))
    click.echo(f"Inserted {inserted} task(s) into call {call_id}.")


@cli.command("respond-availability")
@click.option("--call-id", required=True, help="VolunteerCall.id to respond against")
@click.option("--count", type=int, default=24, show_default=True)
def respond_availability_cmd(call_id: str, count: int) -> None:
    """Have COUNT random volunteers submit availability for the call."""
    responded = asyncio.run(_respond_availability(call_id, count))
    click.echo(f"{responded} volunteer(s) responded to call {call_id}.")


if __name__ == "__main__":
    cli()
