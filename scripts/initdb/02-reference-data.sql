-- Volunteer Call System — Demo Seed Data

-- Staff
INSERT INTO people (id, first_name, last_name, email, phone, skill_category, active) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Sarah', 'Admin', 'sarah@rtaff.org', '703-555-0101', 'skilled', true),
    ('00000000-0000-0000-0000-000000000002', 'Mike', 'Coordinator', 'mike@rtaff.org', '703-555-0102', 'skilled', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000001', 'staff'),
    ('00000000-0000-0000-0000-000000000002', 'staff');

-- Team leaders
INSERT INTO people (id, first_name, last_name, email, phone, skill_category, active) VALUES
    ('00000000-0000-0000-0000-000000000010', 'Tom', 'Builder', 'tom.builder@example.com', '703-555-0201', 'skilled', true),
    ('00000000-0000-0000-0000-000000000011', 'Lisa', 'Carpenter', 'lisa.carpenter@example.com', '703-555-0202', 'skilled', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000010', 'team_leader'),
    ('00000000-0000-0000-0000-000000000010', 'volunteer'),
    ('00000000-0000-0000-0000-000000000011', 'team_leader'),
    ('00000000-0000-0000-0000-000000000011', 'volunteer');

-- Volunteers
INSERT INTO people (id, first_name, last_name, email, phone, skill_category, active) VALUES
    ('00000000-0000-0000-0000-000000000020', 'Alex', 'Volunteer', 'alex.v@example.com', '703-555-0301', 'unskilled', true),
    ('00000000-0000-0000-0000-000000000021', 'Beth', 'Helper', 'beth.h@example.com', '703-555-0302', 'skilled', true),
    ('00000000-0000-0000-0000-000000000022', 'Chris', 'Worker', 'chris.w@example.com', '703-555-0303', 'unskilled', true),
    ('00000000-0000-0000-0000-000000000023', 'Dana', 'Fixer', 'dana.f@example.com', '703-555-0304', 'skilled', true),
    ('00000000-0000-0000-0000-000000000024', 'Eric', 'Painter', 'eric.p@example.com', '703-555-0305', 'unskilled', true),
    ('00000000-0000-0000-0000-000000000025', 'Fiona', 'Plumber', 'fiona.p@example.com', '703-555-0306', 'skilled', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000020', 'volunteer'),
    ('00000000-0000-0000-0000-000000000021', 'volunteer'),
    ('00000000-0000-0000-0000-000000000022', 'volunteer'),
    ('00000000-0000-0000-0000-000000000023', 'volunteer'),
    ('00000000-0000-0000-0000-000000000024', 'volunteer'),
    ('00000000-0000-0000-0000-000000000025', 'volunteer');
