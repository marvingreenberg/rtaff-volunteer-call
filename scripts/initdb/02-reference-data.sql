-- Volunteer Call System — Demo Seed Data

-- Staff
INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Sarah', 'Admin', 'sarah@rtaff.org', '703-555-0101', '{}', true),
    ('00000000-0000-0000-0000-000000000002', 'Mike', 'Coordinator', 'mike@rtaff.org', '703-555-0102', '{}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000001', 'staff'),
    ('00000000-0000-0000-0000-000000000002', 'staff');

-- Team leaders
INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000010', 'Tom', 'Builder', 'tom.builder@example.com', '703-555-0201', '{carpentry}', true),
    ('00000000-0000-0000-0000-000000000011', 'Lisa', 'Carpenter', 'lisa.carpenter@example.com', '703-555-0202', '{carpentry,electrical}', true),
    -- Carmen is the all-programs team lead: belongs to RTX *and* the
    -- single-task programs (ACR, RAMP, LIFT) so the team-lead pulldown
    -- has a candidate for every program out of the box.
    ('00000000-0000-0000-0000-000000000012', 'Carmen', 'Lead', 'carmen.lead@example.com', '703-555-0203', '{carpentry,electrical,plumbing,hvac}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000010', 'team_leader'),
    ('00000000-0000-0000-0000-000000000010', 'volunteer'),
    ('00000000-0000-0000-0000-000000000011', 'team_leader'),
    ('00000000-0000-0000-0000-000000000011', 'volunteer'),
    ('00000000-0000-0000-0000-000000000012', 'team_leader'),
    ('00000000-0000-0000-0000-000000000012', 'volunteer');

-- Volunteers
INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000020', 'Alex', 'Volunteer', 'alex.v@example.com', '703-555-0301', '{}', true),
    ('00000000-0000-0000-0000-000000000021', 'Beth', 'Helper', 'beth.h@example.com', '703-555-0302', '{electrical}', true),
    ('00000000-0000-0000-0000-000000000022', 'Chris', 'Worker', 'chris.w@example.com', '703-555-0303', '{}', true),
    ('00000000-0000-0000-0000-000000000023', 'Dana', 'Fixer', 'dana.f@example.com', '703-555-0304', '{hvac}', true),
    ('00000000-0000-0000-0000-000000000024', 'Eric', 'Painter', 'eric.p@example.com', '703-555-0305', '{}', true),
    ('00000000-0000-0000-0000-000000000025', 'Fiona', 'Plumber', 'fiona.p@example.com', '703-555-0306', '{plumbing}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000020', 'volunteer'),
    ('00000000-0000-0000-0000-000000000021', 'volunteer'),
    ('00000000-0000-0000-0000-000000000022', 'volunteer'),
    ('00000000-0000-0000-0000-000000000023', 'volunteer'),
    ('00000000-0000-0000-0000-000000000024', 'volunteer'),
    ('00000000-0000-0000-0000-000000000025', 'volunteer');

-- Program memberships: every existing volunteer/team-leader joins RTX by default.
-- RTX is the primary program; admins add ACR / RAMP / LIFT memberships per-person
-- via the people editor as those programs activate.
INSERT INTO volunteer_programs (person_id, program) VALUES
    ('00000000-0000-0000-0000-000000000010', 'RTX'),
    ('00000000-0000-0000-0000-000000000011', 'RTX'),
    -- Carmen is a member of every program so the single-task program
    -- workflows have a default team-lead candidate.
    ('00000000-0000-0000-0000-000000000012', 'RTX'),
    ('00000000-0000-0000-0000-000000000012', 'ACR'),
    ('00000000-0000-0000-0000-000000000012', 'RAMP'),
    ('00000000-0000-0000-0000-000000000012', 'LIFT'),
    ('00000000-0000-0000-0000-000000000020', 'RTX'),
    ('00000000-0000-0000-0000-000000000021', 'RTX'),
    ('00000000-0000-0000-0000-000000000022', 'RTX'),
    ('00000000-0000-0000-0000-000000000023', 'RTX'),
    ('00000000-0000-0000-0000-000000000024', 'RTX'),
    ('00000000-0000-0000-0000-000000000025', 'RTX');
