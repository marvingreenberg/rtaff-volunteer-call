-- Volunteer Call System — Database Schema

-- Enum types
CREATE TYPE skill AS ENUM ('plumbing', 'electrical', 'carpentry', 'hvac');
CREATE TYPE program AS ENUM ('RTX', 'ACR', 'RAMP', 'LIFT');
CREATE TYPE roletype AS ENUM ('staff', 'team_leader', 'volunteer');
CREATE TYPE notificationpreference AS ENUM ('email', 'sms', 'both');
CREATE TYPE notificationdetaillevel AS ENUM ('summary', 'full');
CREATE TYPE subscriptionstatus AS ENUM ('active', 'paused', 'unsubscribed');
CREATE TYPE callstatus AS ENUM ('draft', 'open', 'closed');
CREATE TYPE taskstatus AS ENUM ('open', 'full', 'cancelled');
CREATE TYPE assignmentrole AS ENUM ('team_leader', 'volunteer');
CREATE TYPE notificationtype AS ENUM ('call_invite', 'assignment', 'call_thanks', 'assignment_update');
CREATE TYPE sloteventtype AS ENUM ('postponed', 'cancelled', 'rescheduled');

-- People
CREATE TABLE people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    skills skill[] NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    access_token VARCHAR(64) UNIQUE,
    notification_preference notificationpreference NOT NULL DEFAULT 'email',
    notification_detail_level notificationdetaillevel NOT NULL DEFAULT 'full',
    subscription_status subscriptionstatus NOT NULL DEFAULT 'active',
    pause_start DATE,
    pause_end DATE,
    -- Calendar integration: bearer-secret iCal URL pasted by the user.
    -- Never returned in API responses; only the boolean "connected" derives.
    calendar_url VARCHAR(2048),
    calendar_provider VARCHAR(20),
    calendar_url_added_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_people_access_token ON people(access_token);

-- Person roles
CREATE TABLE person_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role roletype NOT NULL,
    UNIQUE(person_id, role)
);

-- Program memberships (volunteer × program join table).
-- Per-program metadata lives here; aggregate stats are computed via JOINs.
CREATE TABLE volunteer_programs (
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    program program NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (person_id, program)
);

-- Volunteer calls
CREATE TABLE volunteer_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    program program NOT NULL,
    status callstatus NOT NULL DEFAULT 'draft',
    notes TEXT,
    created_by_id UUID REFERENCES people(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tasks (within volunteer calls)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volunteer_call_id UUID NOT NULL REFERENCES volunteer_calls(id) ON DELETE CASCADE,
    short_description VARCHAR(500) NOT NULL,
    date DATE,
    time_start TIME,
    time_end TIME,
    address VARCHAR(500),
    city VARCHAR(100),
    team_lead_id UUID REFERENCES people(id),
    volunteers_needed INTEGER NOT NULL DEFAULT 4,
    skilled_needed INTEGER NOT NULL DEFAULT 0,
    status taskstatus NOT NULL DEFAULT 'open',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Volunteer availability
CREATE TABLE volunteer_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volunteer_call_id UUID NOT NULL REFERENCES volunteer_calls(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    max_tasks_per_week INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(volunteer_call_id, person_id, task_id)
);

-- Team assignments
CREATE TABLE team_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role assignmentrole NOT NULL DEFAULT 'volunteer',
    confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(task_id, person_id)
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    type notificationtype NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    link VARCHAR(500),
    read BOOLEAN NOT NULL DEFAULT FALSE,
    call_id UUID REFERENCES volunteer_calls(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Slot events (task schedule changes)
CREATE TABLE slot_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type sloteventtype NOT NULL,
    reason TEXT NOT NULL,
    new_date DATE,
    created_by_id UUID REFERENCES people(id),
    notified_people JSONB NOT NULL DEFAULT '[]',
    cc_people JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
