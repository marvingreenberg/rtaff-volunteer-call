"""Baseline schema — all tables, types, and reference data.

Revision ID: 001
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    op.execute("CREATE TYPE programtype AS ENUM ('RTX', 'ACR', 'RAMP', 'LIFT', 'NRD')")
    op.execute(
        "CREATE TYPE projectstatus AS ENUM ('intake', 'assessment', 'ready_to_sign', 'signed', 'planning', 'planned', 'scheduled', 'in_progress', 'completed', 'archived')"
    )
    op.execute(
        "CREATE TYPE checklistarea AS ENUM ('exterior', 'entrance', 'interior_general', 'kitchen', 'laundry_utility', 'bathroom_1', 'bathroom_2', 'bathroom_3', 'other')"
    )
    op.execute(
        "CREATE TYPE jobcategory AS ENUM ('general', 'electrical', 'plumbing', 'carpentry', 'detectors', 'other')"
    )
    op.execute("CREATE TYPE skillcategory AS ENUM ('skilled', 'unskilled', 'unknown')")
    op.execute("CREATE TYPE roletype AS ENUM ('staff', 'team_leader', 'volunteer')")
    op.execute("CREATE TYPE signerrole AS ENUM ('homeowner', 'team_leader')")
    op.execute(
        "CREATE TYPE itemcategory AS ENUM ('exterior', 'interior', 'kitchen', 'laundry_utility', 'bathroom', 'general')"
    )

    # Homeowners
    op.create_table(
        "homeowners",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_secondary", sa.String(255)),
        sa.Column("street_address", sa.String(500), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("zip_code", sa.String(20), nullable=False),
        sa.Column("phone_primary", sa.String(50), nullable=False),
        sa.Column("phone_secondary", sa.String(50)),
        sa.Column("alternate_contact_name", sa.String(255)),
        sa.Column("alternate_contact_relationship", sa.String(100)),
        sa.Column("alternate_contact_phone", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Funding sources
    op.create_table(
        "funding_sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("program_type", sa.String(10)),
        sa.Column("geographic_area", sa.String(100)),
    )

    # People
    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column(
            "skill_category",
            sa.Enum("skilled", "unskilled", "unknown", name="skillcategory", create_type=False),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "volunteer_agreement_current", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("volunteer_agreement_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("access_token", sa.String(64), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_people_access_token", "people", ["access_token"], unique=True)

    # Person roles
    op.create_table(
        "person_roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "person_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("people.id"), nullable=False
        ),
        sa.Column(
            "role",
            sa.Enum("staff", "team_leader", "volunteer", name="roletype", create_type=False),
            nullable=False,
        ),
    )

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "homeowner_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("homeowners.id"),
            nullable=False,
        ),
        sa.Column(
            "program_type",
            sa.Enum("RTX", "ACR", "RAMP", "LIFT", "NRD", name="programtype", create_type=False),
            nullable=False,
            server_default="RTX",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "intake",
                "assessment",
                "ready_to_sign",
                "signed",
                "planning",
                "planned",
                "scheduled",
                "in_progress",
                "completed",
                "archived",
                name="projectstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="intake",
        ),
        sa.Column("account_code", sa.String(50)),
        sa.Column(
            "funding_source_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("funding_sources.id")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Assessments
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("visit_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lead_assessor_name", sa.String(255), nullable=True),
        sa.Column("assessor_names", sa.JSON(), server_default="[]"),
        sa.Column(
            "assessment_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "visit_number", name="uq_assessment_project_visit"),
    )

    # Assessment items
    op.create_table(
        "assessment_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("assessments.id"),
            nullable=False,
        ),
        sa.Column(
            "area",
            sa.Enum(
                "exterior",
                "entrance",
                "interior_general",
                "kitchen",
                "laundry_utility",
                "bathroom_1",
                "bathroom_2",
                "bathroom_3",
                "other",
                name="checklistarea",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("repair_needed", sa.Boolean()),
        sa.Column("details", sa.Text()),
        sa.Column("measurement", sa.String(100), nullable=True),
        sa.Column(
            "job_category",
            sa.Enum(
                "general",
                "electrical",
                "plumbing",
                "carpentry",
                "detectors",
                "other",
                name="jobcategory",
                create_type=False,
            ),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Assessment assessors
    op.create_table(
        "assessment_assessors",
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("assessments.id"),
            primary_key=True,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("people.id"),
            primary_key=True,
        ),
        sa.Column("is_lead", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Photos
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "assessment_item_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("assessment_items.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Homeowner agreements
    op.create_table(
        "homeowner_agreements",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("pdf_data", sa.LargeBinary(), nullable=False),
        sa.Column("signed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("signed_date", sa.Date()),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
    )

    # Agreement signatures
    op.create_table(
        "agreement_signatures",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "agreement_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("homeowner_agreements.id"),
            nullable=False,
        ),
        sa.Column(
            "signer_role",
            sa.Enum("homeowner", "team_leader", name="signerrole", create_type=False),
            nullable=False,
        ),
        sa.Column("signer_name", sa.String(255), nullable=False),
        sa.Column("signature_data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "signed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Health & safety priorities
    op.create_table(
        "health_safety_priorities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Item-to-priority mapping
    op.create_table(
        "item_priority_mappings",
        sa.Column("item_key", sa.String(100), primary_key=True),
        sa.Column(
            "priority_id",
            sa.Integer(),
            sa.ForeignKey("health_safety_priorities.id"),
            primary_key=True,
        ),
    )

    # Assessment item priorities (many-to-many)
    op.create_table(
        "assessment_item_priorities",
        sa.Column(
            "assessment_item_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("assessment_items.id"),
            primary_key=True,
        ),
        sa.Column(
            "priority_id",
            sa.Integer(),
            sa.ForeignKey("health_safety_priorities.id"),
            primary_key=True,
        ),
    )

    # Inventory items
    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "category",
            sa.Enum(
                "exterior",
                "interior",
                "kitchen",
                "laundry_utility",
                "bathroom",
                "general",
                name="itemcategory",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Work plans
    op.create_table(
        "work_plans",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("people.id")),
        sa.Column("team_size_required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skilled_volunteers_needed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skill_types_needed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Planned repairs
    op.create_table(
        "planned_repairs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "work_plan_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("work_plans.id"),
            nullable=False,
        ),
        sa.Column(
            "assessment_item_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("assessment_items.id"),
            nullable=False,
        ),
        sa.Column("in_scope", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("requires_contractor", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text()),
    )

    # Material requirements
    op.create_table(
        "material_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "work_plan_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("work_plans.id"),
            nullable=False,
        ),
        sa.Column(
            "inventory_item_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("inventory_items.id")
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estimated_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # --- Seed reference data ---
    _seed_funding_sources()
    _seed_health_safety_priorities()
    _seed_inventory_items()


def _seed_funding_sources() -> None:
    op.execute("""
        INSERT INTO funding_sources (id, code, name, program_type, geographic_area) VALUES
        (gen_random_uuid()::text, '01 RT Arl',  'Rebuilding Together Arlington', 'NRD', 'Arlington'),
        (gen_random_uuid()::text, '02 YR Arl',  'Year-Round Arlington',          'RTX', 'Arlington'),
        (gen_random_uuid()::text, '03 RT FFX',  'Rebuilding Together Fairfax',   'NRD', 'Fairfax'),
        (gen_random_uuid()::text, '04 YR FFX',  'Year-Round Fairfax',            'RTX', 'Fairfax'),
        (gen_random_uuid()::text, '14 RTX ARL', 'RT Express Arlington',          'RTX', 'Arlington'),
        (gen_random_uuid()::text, '15 RTX FFX', 'RT Express Fairfax',            'RTX', 'Fairfax')
    """)


def _seed_health_safety_priorities() -> None:
    priorities = [
        (1, "Residents can safely enter and leave the home"),
        (2, "The roof is watertight"),
        (3, "Rainwater is effectively shed and directed away from the structure"),
        (4, "Exterior walls have no gaps/cracks/holes that allow intrusion of bulk moisture/pests"),
        (5, "Windows and exterior doors open and close, lock securely and seal well"),
        (6, "Home is free of live infestation of pests, and sources of attraction are removed"),
        (7, "The numerals in the property's street address are clearly visible from the street"),
        (8, "A working smoke detector is on each floor and in or near bedrooms"),
        (9, "A working CO detector protects home with gas appliances or attached garage"),
        (10, "A currently dated Class ABC fire extinguisher is available in or near the kitchen"),
        (11, "Water and space heating appliances that produce CO exhaust outside"),
        (12, "No known electrical hazards are present, and kitchens and baths have GFCIs"),
        (13, "Residents have access to a working water heater, refrigerator and range"),
        (14, "The kitchen and bathrooms have an exhaust fan vented outside"),
        (15, "Residents have access to a working sink, toilet and bathtub or shower"),
        (16, "Residents who need help bathing/toileting have appropriate bathroom mods"),
        (17, "Residents at risk of falls have grab bars well located and securely fastened"),
        (18, "Stairs and steps have secure handrails that meet residents' needs"),
        (19, "Main rooms and stairs are free of tripping hazards"),
        (20, "Carpeting that creates a health and safety hazard has been replaced"),
        (21, "Clothes dryer, if present, vents outside w/ metal duct and unobstructed airflow"),
        (22, "Residents can maintain the interior temperature in a comfortable range"),
        (23, "Lighting is adequate for daily tasks and crossing rooms/stairs/entrances"),
        (24, "Interior paint, wall covering and drywall is intact"),
        (25, "The home is free of active water leaks and serious moisture/mold problems"),
    ]
    for pid, desc in priorities:
        escaped = desc.replace("'", "''")
        op.execute(
            f"INSERT INTO health_safety_priorities (id, description, active) VALUES ({pid}, '{escaped}', true)"
        )

    mappings = {
        "house_numbers": [7],
        "gutters": [3],
        "downspouts": [3],
        "gaps_cracks_holes": [4],
        "exterior_electrical": [12],
        "exterior_stoop_steps_sidewalk": [1, 18],
        "exterior_handrail": [1, 18],
        "storm_door": [5],
        "exterior_door": [5],
        "weatherstripping_sweep": [5],
        "wheelchair_ramp": [1],
        "smoke_co_detectors": [8, 9],
        "tripping_hazards": [19],
        "lighting": [23],
        "stair_rail": [18],
        "stair_lift": [1],
        "fire_extinguisher": [10],
        "kitchen_faucet_drain": [15],
        "garbage_disposal": [15],
        "dishwasher": [13],
        "stove_microwave": [13],
        "range_hood_exhaust_fan": [14],
        "kitchen_lighting": [23],
        "kitchen_gfci": [12],
        "dryer_vent": [21],
        "clothes_dryer": [21],
        "water_heater": [11, 13],
        "furnace_hvac": [11, 22],
        "laundry_gfci": [12],
        "grab_bar_tub_shower": [17],
        "grab_bar_toilet": [17],
        "grab_bar_other": [17],
        "hh_showerhead_stool_noslip": [16],
        "comfort_height_toilet": [16],
        "toilet_safety_rails": [16],
        "toilet_flapper_refill_valve": [15],
        "faucet_drain_shower_controls": [15],
        "bathroom_lighting": [23],
        "exhaust_fan": [14],
        "bathroom_gfci": [12],
        "caulking": [25],
    }
    for item_key, pids in mappings.items():
        for pid in pids:
            op.execute(
                f"INSERT INTO item_priority_mappings (item_key, priority_id) VALUES ('{item_key}', {pid})"
            )


def _seed_inventory_items() -> None:
    items = [
        ("Bathroom sink faucet", "bathroom", 45.00),
        ("CO alarm", "general", 25.00),
        ("Combination smoke/CO alarm", "general", 35.00),
        ("Dryer duct and clamps", "laundry_utility", 15.00),
        ("Exhaust fan", "bathroom", 30.00),
        ("Faucet aerator", "kitchen", 5.00),
        ("Fire extinguisher", "kitchen", 25.00),
        ("GFCI outlet", "general", 15.00),
        ("Grab bar, 18 inch", "bathroom", 20.00),
        ("Grab bar, 24 inch", "bathroom", 25.00),
        ("Grab bar, 36 inch", "bathroom", 30.00),
        ("Handheld showerhead", "bathroom", 25.00),
        ("Kitchen faucet", "kitchen", 55.00),
        ("Lever door handle", "interior", 20.00),
        ("Smoke alarm", "general", 15.00),
        ("Toilet flapper", "bathroom", 8.00),
        ("Toilet safety frame", "bathroom", 35.00),
    ]
    items_table = sa.table(
        "inventory_items",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("unit_cost", sa.Numeric),
        sa.column("quantity_on_hand", sa.Integer),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        items_table,
        [
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "category": cat,
                "unit_cost": cost,
                "quantity_on_hand": 0,
                "active": True,
            }
            for name, cat, cost in items
        ],
    )


def downgrade() -> None:
    for table in [
        "material_requirements",
        "planned_repairs",
        "work_plans",
        "assessment_item_priorities",
        "item_priority_mappings",
        "health_safety_priorities",
        "agreement_signatures",
        "homeowner_agreements",
        "photos",
        "assessment_assessors",
        "assessment_items",
        "assessments",
        "projects",
        "person_roles",
        "people",
        "funding_sources",
        "homeowners",
        "inventory_items",
    ]:
        op.drop_table(table)

    for enum in [
        "itemcategory",
        "signerrole",
        "roletype",
        "skillcategory",
        "jobcategory",
        "checklistarea",
        "projectstatus",
        "programtype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
