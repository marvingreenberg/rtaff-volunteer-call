-- ===========================================================================
-- Historical volunteer calls + team assignments (demo seed)
-- ===========================================================================
-- Purpose: give the volunteer roster a spread of last_assignment_date values
-- so the fairness signals on the assign page actually fire in the demo —
-- specifically the 😴 badge (bottom quartile of last_assignment_date within
-- the responding pool) and the assignments_trailing_3mo counter.
--
-- We create six archived calls dated 7, 14, 30, 45, 60, and 90 days ago,
-- each with three or four tasks, and we distribute assignments across the
-- volunteer roster so that:
--   - ~12 volunteers were last assigned in the recent calls (7-14 days)
--   - ~14 volunteers were last assigned in mid-range calls (30-45 days)
--   - ~12 volunteers were last assigned in older calls (60-90 days)
--   - ~9 volunteers have never been assigned (null last_assignment_date)
--
-- Volunteer person IDs run 00000000-0000-0000-0000-000000000020..047 in
-- the reference data; this script uses CURRENT_DATE arithmetic so the
-- dates stay relative to whenever the DB is seeded.

DO $$
DECLARE
    v_today DATE := CURRENT_DATE;
BEGIN
    -- ---- Calls (all archived, RTX program) -------------------------------
    INSERT INTO volunteer_calls (id, title, program, status, notes, created_at, updated_at) VALUES
        ('11111111-0000-0000-0000-000000000001', 'Winter Build — 7d ago',  'RTX', 'archived', NULL, NOW(), NOW()),
        ('11111111-0000-0000-0000-000000000002', 'Late Fall Build',         'RTX', 'archived', NULL, NOW(), NOW()),
        ('11111111-0000-0000-0000-000000000003', 'Fall NRD',                'RTX', 'archived', NULL, NOW(), NOW()),
        ('11111111-0000-0000-0000-000000000004', 'Early Fall Weekend',      'RTX', 'archived', NULL, NOW(), NOW()),
        ('11111111-0000-0000-0000-000000000005', 'Summer Build',            'RTX', 'archived', NULL, NOW(), NOW()),
        ('11111111-0000-0000-0000-000000000006', 'Spring NRD',              'RTX', 'archived', NULL, NOW(), NOW())
    ;

    -- ---- Tasks ------------------------------------------------------------
    -- One task per row. The task IDs are 22222222-XXX where XXX = call id
    -- middle bytes + sequence.
    INSERT INTO tasks (id, volunteer_call_id, short_description, date, address, city, volunteers_needed, status, created_at, updated_at) VALUES
        -- Call 1 (7d ago, 3 tasks)
        ('22222222-0000-0000-0000-000000010101', '11111111-0000-0000-0000-000000000001', 'Roof patch', v_today - 7,  '101 Main',  'Arlington',   4, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010102', '11111111-0000-0000-0000-000000000001', 'Bath grab bars', v_today - 7,  '102 Oak',   'Falls Church', 3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010103', '11111111-0000-0000-0000-000000000001', 'Ramp install', v_today - 7,  '103 Pine',  'Vienna',       4, 'full', NOW(), NOW()),
        -- Call 2 (14d ago, 3 tasks)
        ('22222222-0000-0000-0000-000000020201', '11111111-0000-0000-0000-000000000002', 'Drywall',     v_today - 14, '201 Elm',   'Arlington',   4, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020202', '11111111-0000-0000-0000-000000000002', 'Floor refinish', v_today - 14, '202 Maple', 'McLean',     3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020203', '11111111-0000-0000-0000-000000000002', 'Yard cleanup', v_today - 14, '203 Birch', 'Annandale',  4, 'full', NOW(), NOW()),
        -- Call 3 (30d ago, 4 tasks)
        ('22222222-0000-0000-0000-000000030301', '11111111-0000-0000-0000-000000000003', 'Roof patch',  v_today - 30, '301 Ash',   'Falls Church', 3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030302', '11111111-0000-0000-0000-000000000003', 'Painting',    v_today - 30, '302 Cedar', 'Springfield',  3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030303', '11111111-0000-0000-0000-000000000003', 'Gutter clean', v_today - 30, '303 Spruce', 'Vienna',     3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030304', '11111111-0000-0000-0000-000000000003', 'Garage clean', v_today - 30, '304 Willow', 'Reston',     3, 'full', NOW(), NOW()),
        -- Call 4 (45d ago, 4 tasks)
        ('22222222-0000-0000-0000-000000040401', '11111111-0000-0000-0000-000000000004', 'Bath retile', v_today - 45, '401 Walnut', 'Arlington',  3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040402', '11111111-0000-0000-0000-000000000004', 'Door replace', v_today - 45, '402 Hickory', 'Falls Church', 3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040403', '11111111-0000-0000-0000-000000000004', 'Window seal', v_today - 45, '403 Magnolia', 'McLean',    3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040404', '11111111-0000-0000-0000-000000000004', 'Porch repair', v_today - 45, '404 Sycamore', 'Vienna',   3, 'full', NOW(), NOW()),
        -- Call 5 (60d ago, 3 tasks)
        ('22222222-0000-0000-0000-000000050501', '11111111-0000-0000-0000-000000000005', 'Roof patch',  v_today - 60, '501 Holly', 'Springfield',  4, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050502', '11111111-0000-0000-0000-000000000005', 'Drywall',     v_today - 60, '502 Cherry', 'Annandale',   4, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050503', '11111111-0000-0000-0000-000000000005', 'Yard cleanup', v_today - 60, '503 Dogwood', 'Reston',     4, 'full', NOW(), NOW()),
        -- Call 6 (90d ago, 3 tasks)
        ('22222222-0000-0000-0000-000000060601', '11111111-0000-0000-0000-000000000006', 'Floor refinish', v_today - 90, '601 Aspen', 'Arlington',  3, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060602', '11111111-0000-0000-0000-000000000006', 'Gutter clean', v_today - 90, '602 Linden', 'Falls Church', 4, 'full', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060603', '11111111-0000-0000-0000-000000000006', 'Painting',     v_today - 90, '603 Beech', 'Vienna',       3, 'full', NOW(), NOW())
    ;

    -- ---- Team assignments ------------------------------------------------
    -- Volunteer IDs go ...020 through ...066. The blocks below distribute
    -- assignments so that recent calls (7-14d) draw from one block, mid-
    -- range from another, and older from a third. Some overlap so the
    -- trailing_3mo counter has variance.

    INSERT INTO team_assignments (task_id, person_id, role, created_at, updated_at) VALUES
        -- Recent block (7-14d) → these volunteers DON'T qualify for 😴
        ('22222222-0000-0000-0000-000000010101', '00000000-0000-0000-0000-000000000020', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010101', '00000000-0000-0000-0000-000000000021', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010102', '00000000-0000-0000-0000-000000000022', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010102', '00000000-0000-0000-0000-000000000023', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010103', '00000000-0000-0000-0000-000000000024', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000010103', '00000000-0000-0000-0000-000000000025', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020201', '00000000-0000-0000-0000-000000000026', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020201', '00000000-0000-0000-0000-000000000027', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020202', '00000000-0000-0000-0000-000000000028', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020202', '00000000-0000-0000-0000-000000000029', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020203', '00000000-0000-0000-0000-000000000030', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020203', '00000000-0000-0000-0000-000000000031', 'volunteer', NOW(), NOW()),

        -- Mid-range block (30-45d)
        ('22222222-0000-0000-0000-000000030301', '00000000-0000-0000-0000-000000000032', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030301', '00000000-0000-0000-0000-000000000033', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030302', '00000000-0000-0000-0000-000000000034', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030302', '00000000-0000-0000-0000-000000000035', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030303', '00000000-0000-0000-0000-000000000036', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000030304', '00000000-0000-0000-0000-000000000037', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040401', '00000000-0000-0000-0000-000000000038', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040401', '00000000-0000-0000-0000-000000000039', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040402', '00000000-0000-0000-0000-000000000040', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040403', '00000000-0000-0000-0000-000000000041', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040404', '00000000-0000-0000-0000-000000000042', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040404', '00000000-0000-0000-0000-000000000043', 'volunteer', NOW(), NOW()),

        -- Older block (60-90d) → these will land in the 😴 quartile
        ('22222222-0000-0000-0000-000000050501', '00000000-0000-0000-0000-000000000044', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050501', '00000000-0000-0000-0000-000000000045', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050502', '00000000-0000-0000-0000-000000000046', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050502', '00000000-0000-0000-0000-000000000047', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050503', '00000000-0000-0000-0000-000000000048', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050503', '00000000-0000-0000-0000-000000000049', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060601', '00000000-0000-0000-0000-000000000050', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060601', '00000000-0000-0000-0000-000000000051', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060602', '00000000-0000-0000-0000-000000000052', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060602', '00000000-0000-0000-0000-000000000053', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060603', '00000000-0000-0000-0000-000000000054', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000060603', '00000000-0000-0000-0000-000000000055', 'volunteer', NOW(), NOW()),

        -- Some overlap: repeat regulars across calls so trailing_3mo > 1 for them
        ('22222222-0000-0000-0000-000000030301', '00000000-0000-0000-0000-000000000020', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000020201', '00000000-0000-0000-0000-000000000020', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000040402', '00000000-0000-0000-0000-000000000022', 'volunteer', NOW(), NOW()),
        ('22222222-0000-0000-0000-000000050501', '00000000-0000-0000-0000-000000000028', 'volunteer', NOW(), NOW())
    ;

    -- Volunteers ...056 through ...066 (≈9 people) intentionally have NO
    -- assignments — null last_assignment_date, which sorts oldest of all
    -- and helps demonstrate the "include nulls in 😴" rule.
END $$;
