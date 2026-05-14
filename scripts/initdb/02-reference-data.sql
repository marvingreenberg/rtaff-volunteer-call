-- Volunteer Call System — Demo Seed Data
--
-- Real RT-AFF contact roster (deconflicted from rt-aff-contacts.txt).
-- Names with no first/last in the source are assigned plausible invented
-- names derived from the email local-part when possible, otherwise
-- fabricated. The first email per person is the primary (notification)
-- address; additional addresses become person_login_aliases rows.
--
-- UUID ranges:
--   0001-0005 admins (5)
--   0010-0019 team leads (10)
--   0020-0066 volunteers (47)

-- ===========================================================================
-- Admins
-- ===========================================================================

INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Darek',  'Newby',    'darek@rebuildingtogether-aff.org',  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000002', 'Dante',  'Calfayan', 'dantec@rebuildingtogether-aff.org', NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000003', 'Don',    'Ryan',     'don@rebuildingtogether-aff.org',    NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000004', 'Patti',  'Klein',    'pattik@rebuildingtogether-aff.org', NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000005', 'Daphne', 'Lawson',   'daphnel@rebuildingtogether-aff.org',NULL, '{}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000001', 'staff'),
    ('00000000-0000-0000-0000-000000000002', 'staff'),
    ('00000000-0000-0000-0000-000000000003', 'staff'),
    ('00000000-0000-0000-0000-000000000004', 'staff'),
    ('00000000-0000-0000-0000-000000000005', 'staff');

-- ===========================================================================
-- Team leads (also have a 'volunteer' role so they appear in volunteer lookups)
-- ===========================================================================

INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000010', 'Bard',    'Jackson',     'bard.jackson105@gmail.com',  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000011', 'Charles', 'Monfort',     'cmonfort@martin-blanck.com', NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000012', 'David',   'Throckmorton','davidthrock@yahoo.com',      NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000013', 'Gordon',  'Meuse',       'gmeuse2@gmail.com',          NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000014', 'Jim',     'Dillon',      'jjdill3076@aol.com',         NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000015', 'Juan',    'Ballve',      'jballve1@hotmail.com',       NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000016', 'Leon',    'Rubis',       'lrubis218@gmail.com',        NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000017', 'Lou',     'Wood',        'lgwmailxfer@yahoo.com',      NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000018', 'Mark',    'Heslep',      'mheslep@gmail.com',          NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000019', 'William', 'Marshall',    'wajmjr@gmail.com',           NULL, '{}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000010', 'team_leader'),
    ('00000000-0000-0000-0000-000000000010', 'volunteer'),
    ('00000000-0000-0000-0000-000000000011', 'team_leader'),
    ('00000000-0000-0000-0000-000000000011', 'volunteer'),
    ('00000000-0000-0000-0000-000000000012', 'team_leader'),
    ('00000000-0000-0000-0000-000000000012', 'volunteer'),
    ('00000000-0000-0000-0000-000000000013', 'team_leader'),
    ('00000000-0000-0000-0000-000000000013', 'volunteer'),
    ('00000000-0000-0000-0000-000000000014', 'team_leader'),
    ('00000000-0000-0000-0000-000000000014', 'volunteer'),
    ('00000000-0000-0000-0000-000000000015', 'team_leader'),
    ('00000000-0000-0000-0000-000000000015', 'volunteer'),
    ('00000000-0000-0000-0000-000000000016', 'team_leader'),
    ('00000000-0000-0000-0000-000000000016', 'volunteer'),
    ('00000000-0000-0000-0000-000000000017', 'team_leader'),
    ('00000000-0000-0000-0000-000000000017', 'volunteer'),
    ('00000000-0000-0000-0000-000000000018', 'team_leader'),
    ('00000000-0000-0000-0000-000000000018', 'volunteer'),
    ('00000000-0000-0000-0000-000000000019', 'team_leader'),
    ('00000000-0000-0000-0000-000000000019', 'volunteer');

-- ===========================================================================
-- Volunteers (47 — names invented where the source had email-only)
-- ===========================================================================

INSERT INTO people (id, first_name, last_name, email, phone, skills, active) VALUES
    ('00000000-0000-0000-0000-000000000020', 'Vick',     'Fisher',       'vgfisher@gmail.com',                  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000021', 'Pat',      'Mercer',       '8512@cox.net',                        NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000022', 'Ana',      'Garcia',       'anag@rebuildingtogether-aff.org',     NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000023', 'Barb',     'Dale',         'barbdmale@yahoo.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000024', 'Bryan',    'Cobb',         'bcobb2014@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000025', 'Bill',     'Gore',         'billgore@cox.net',                    NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000026', 'Bob',      'Austin',       'bob.austin@verizon.net',              NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000027', 'Marc',     'Breit',        'breitmarc@yahoo.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000028', 'Chuck',    'Connell',      'chuckcon1@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000029', 'CJ',       'Kim',          'cjk22033@gmail.com',                  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000030', 'CJ',       'Murray',       'cjmurray178@gmail.com',               NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000031', 'Dave',     'Reynolds',     'dave@rebuildingtogether-aff.org',     NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000032', 'David',    'McCubbin',     'dcmccubbin@fastmail.com',             NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000033', 'Doug',     'Henderson',    'dhlinva@verizon.net',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000034', 'Mike',     'Dimond',       'dimondedad@aol.com',                  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000035', 'Don',      'Travers',      'donontravel@yahoo.com',               NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000036', 'Don',      'Witman',       'donwitman@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000037', 'Ed',       'Porter',       'edporter6@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000038', 'Frank',    'Roberts',      'frank.roberts@verizon.net',           NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000039', 'Fritz',    'Schmidt',      'fritzs@rebuildingtogether-aff.org',   NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000040', 'JC',       'Gould',        'gouldjc@gmail.com',                   NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000041', 'Jerry',    'Huther',       'hutherj@verizon.net',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000042', 'Jirina',   'Kent',         'jirinakent@gmail.com',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000043', 'Jenny',    'Lane',         'jlane16@gmail.com',                   NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000044', 'Joe',      'Maher',        'jmahersss@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000045', 'Kira',     'Mittelholtz',  'kcmittelholtz@gmail.com',             NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000046', 'Kevin',    'Sbruzzi',      'kevinsbru@verizon.net',               NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000047', 'Lander',   'Allin',        'landerallin@gmail.com',               NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000048', 'Lex',      'Walker',       'lex1125@gmail.com',                   NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000049', 'Mamoni',   'Patel',        'mamoni530@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000050', 'Mark',     'Olson',        'mark@olson.us',                       NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000051', 'Morgan',   'Carey',        'mogencare@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000052', 'Nancy',    'Rowan',        'nancyro2no@gmail.com',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000053', 'Carter',   'Brown',        'newtoncb59@gmail.com',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000054', 'Nick',     'Fagnoni',      'nfagnoni@yahoo.com',                  NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000055', 'Paul',     'Gunning',      'paulm.gunning@verizon.net',           NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000056', 'Pat',      'Jaden',        'ptjaden@verizon.net',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000057', 'Barry',    'Richardson',   'richardsonbarry4332@gmail.com',       NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000058', 'Robert',   'Steinle',      'rmsteinle@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000059', 'Ruth',     'Floresco',     'ruth.florescoreas@fairfaxcounty.gov', NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000060', 'Sabrina',  'Olla',         'sabriola1@gmail.com',                 NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000061', 'Mark',     'Scherger',     'schergermark@gmail.com',              NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000062', 'Scott',    'Hursh',        'scotthursh@yahoo.com',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000063', 'Steve',    'Turchen',      'sturchen@verizon.net',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000064', 'Thomas',   'Fay',          'thomaskfay@gmail.com',                NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000065', 'Tom',      'Mason',        'tmason1282@outlook.com',              NULL, '{}', true),
    ('00000000-0000-0000-0000-000000000066', 'William',  'Swedish',      'wjswedish@gmail.com',                 NULL, '{}', true);

INSERT INTO person_roles (person_id, role) VALUES
    ('00000000-0000-0000-0000-000000000020', 'volunteer'),
    ('00000000-0000-0000-0000-000000000021', 'volunteer'),
    ('00000000-0000-0000-0000-000000000022', 'volunteer'),
    ('00000000-0000-0000-0000-000000000023', 'volunteer'),
    ('00000000-0000-0000-0000-000000000024', 'volunteer'),
    ('00000000-0000-0000-0000-000000000025', 'volunteer'),
    ('00000000-0000-0000-0000-000000000026', 'volunteer'),
    ('00000000-0000-0000-0000-000000000027', 'volunteer'),
    ('00000000-0000-0000-0000-000000000028', 'volunteer'),
    ('00000000-0000-0000-0000-000000000029', 'volunteer'),
    ('00000000-0000-0000-0000-000000000030', 'volunteer'),
    ('00000000-0000-0000-0000-000000000031', 'volunteer'),
    ('00000000-0000-0000-0000-000000000032', 'volunteer'),
    ('00000000-0000-0000-0000-000000000033', 'volunteer'),
    ('00000000-0000-0000-0000-000000000034', 'volunteer'),
    ('00000000-0000-0000-0000-000000000035', 'volunteer'),
    ('00000000-0000-0000-0000-000000000036', 'volunteer'),
    ('00000000-0000-0000-0000-000000000037', 'volunteer'),
    ('00000000-0000-0000-0000-000000000038', 'volunteer'),
    ('00000000-0000-0000-0000-000000000039', 'volunteer'),
    ('00000000-0000-0000-0000-000000000040', 'volunteer'),
    ('00000000-0000-0000-0000-000000000041', 'volunteer'),
    ('00000000-0000-0000-0000-000000000042', 'volunteer'),
    ('00000000-0000-0000-0000-000000000043', 'volunteer'),
    ('00000000-0000-0000-0000-000000000044', 'volunteer'),
    ('00000000-0000-0000-0000-000000000045', 'volunteer'),
    ('00000000-0000-0000-0000-000000000046', 'volunteer'),
    ('00000000-0000-0000-0000-000000000047', 'volunteer'),
    ('00000000-0000-0000-0000-000000000048', 'volunteer'),
    ('00000000-0000-0000-0000-000000000049', 'volunteer'),
    ('00000000-0000-0000-0000-000000000050', 'volunteer'),
    ('00000000-0000-0000-0000-000000000051', 'volunteer'),
    ('00000000-0000-0000-0000-000000000052', 'volunteer'),
    ('00000000-0000-0000-0000-000000000053', 'volunteer'),
    ('00000000-0000-0000-0000-000000000054', 'volunteer'),
    ('00000000-0000-0000-0000-000000000055', 'volunteer'),
    ('00000000-0000-0000-0000-000000000056', 'volunteer'),
    ('00000000-0000-0000-0000-000000000057', 'volunteer'),
    ('00000000-0000-0000-0000-000000000058', 'volunteer'),
    ('00000000-0000-0000-0000-000000000059', 'volunteer'),
    ('00000000-0000-0000-0000-000000000060', 'volunteer'),
    ('00000000-0000-0000-0000-000000000061', 'volunteer'),
    ('00000000-0000-0000-0000-000000000062', 'volunteer'),
    ('00000000-0000-0000-0000-000000000063', 'volunteer'),
    ('00000000-0000-0000-0000-000000000064', 'volunteer'),
    ('00000000-0000-0000-0000-000000000065', 'volunteer'),
    ('00000000-0000-0000-0000-000000000066', 'volunteer');

-- ===========================================================================
-- Login aliases for people with multiple email addresses
-- ===========================================================================
-- Darek Newby has three addresses in the source file (two RT-AFF, one gmail).
-- Don Ryan has both his RT-AFF address and a personal gmail.
-- Charles Monfort's <cmonfort@comcast.net> appearance in the volunteers
-- block is treated as a personal alias on the team-lead record.

INSERT INTO person_login_aliases (person_id, email) VALUES
    ('00000000-0000-0000-0000-000000000001', 'darekn@rebuildingtogether-aff.org'),
    ('00000000-0000-0000-0000-000000000001', 'dlnpublic0@gmail.com'),
    ('00000000-0000-0000-0000-000000000003', 'donryanemail@gmail.com'),
    ('00000000-0000-0000-0000-000000000011', 'cmonfort@comcast.net');

-- ===========================================================================
-- Program memberships
-- ===========================================================================
-- Everyone joins RTX (the primary program). William Marshall additionally
-- joins ACR/RAMP/LIFT so the single-task program workflows have a default
-- team-lead candidate without any admin intervention (this replaces the
-- previous Carmen-as-all-programs-lead pattern).

INSERT INTO volunteer_programs (person_id, program)
SELECT id, 'RTX'::program FROM people;

INSERT INTO volunteer_programs (person_id, program) VALUES
    ('00000000-0000-0000-0000-000000000019', 'ACR'),
    ('00000000-0000-0000-0000-000000000019', 'RAMP'),
    ('00000000-0000-0000-0000-000000000019', 'LIFT');
