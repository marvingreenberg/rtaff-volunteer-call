#!/usr/bin/env bash
# Demo scenario: full volunteer call lifecycle (API-only, headless)
#
# For a visual browser-based demo, see: frontend/e2e/demo-scenario.spec.ts
#   Run with: cd frontend && pnpm exec playwright test e2e/demo-scenario.spec.ts --headed
#
# Prerequisites: backend running on :8000, DB seeded with reference data, DEMO_MODE=true
#
# Flow:
#   1. Admin logs in, creates a volunteer call with 2 tasks
#   2. Admin opens the call and sends invites
#   3. Two volunteers "click the link" (login), view jobs, submit availability
#   4. Admin assigns volunteers and closes the call

set -euo pipefail

API="http://localhost:8000"
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

step() { echo -e "\n${BOLD}── $1${RESET}"; }
info() { echo -e "${DIM}   $1${RESET}"; }

# --- Helper: login via demo mode, extract token ---
login() {
    local email="$1"
    local resp
    resp=$(curl -sf "$API/auth/login" -H 'Content-Type: application/json' \
        -d "{\"email\": \"$email\"}")
    echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['demo_token'])"
}

# --- Helper: authenticated request ---
authed() {
    local token="$1"; shift
    local method="$1"; shift
    local path="$1"; shift
    curl -sf -X "$method" "$API$path" \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        "$@"
}

# --- Helper: pretty-print JSON ---
pp() { python3 -m json.tool; }

# =============================================================================
step "1. Admin logs in"
ADMIN_TOKEN=$(login "sarah@rtaff.org")
info "Sarah Admin authenticated (token: ${ADMIN_TOKEN:0:12}...)"

# =============================================================================
step "2. Admin creates a volunteer call"
CALL=$(curl -sf "$API/volunteer-calls" -H 'Content-Type: application/json' \
    -d '{
        "title": "June 2026 Weekend Build",
        "notes": "Two-day build event in Arlington and Falls Church"
    }')
CALL_ID=$(echo "$CALL" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Created call: $CALL_ID"
echo "$CALL" | pp

# =============================================================================
step "3. Admin adds tasks to the call"
TASK1=$(curl -sf "$API/volunteer-calls/$CALL_ID/tasks" -H 'Content-Type: application/json' \
    -d '{
        "short_description": "Kitchen remodel — Arlington",
        "date": "2026-06-13",
        "time_start": "08:00:00",
        "time_end": "16:00:00",
        "address": "1234 Oak St, Arlington, VA 22201",
        "city": "Arlington",
        "team_lead_id": "00000000-0000-0000-0000-000000000010",
        "volunteers_needed": 4,
        "skilled_needed": 2
    }')
TASK1_ID=$(echo "$TASK1" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Task 1: Kitchen remodel ($TASK1_ID)"

TASK2=$(curl -sf "$API/volunteer-calls/$CALL_ID/tasks" -H 'Content-Type: application/json' \
    -d '{
        "short_description": "Deck repair — Falls Church",
        "date": "2026-06-14",
        "time_start": "09:00:00",
        "time_end": "14:00:00",
        "address": "5678 Elm Ave, Falls Church, VA 22042",
        "city": "Falls Church",
        "team_lead_id": "00000000-0000-0000-0000-000000000011",
        "volunteers_needed": 3,
        "skilled_needed": 1
    }')
TASK2_ID=$(echo "$TASK2" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Task 2: Deck repair ($TASK2_ID)"

# =============================================================================
step "4. Admin opens the call"
curl -sf "$API/volunteer-calls/$CALL_ID" -X PUT -H 'Content-Type: application/json' \
    -d '{"status": "open"}' | pp

# =============================================================================
step "5. Admin sends invites to all volunteers"
INVITE_RESULT=$(curl -sf "$API/volunteer-calls/$CALL_ID/send-invites" -X POST \
    -H 'Content-Type: application/json')
info "Invite result:"
echo "$INVITE_RESULT" | pp

# =============================================================================
step "6. Volunteer Alex clicks the invite link and logs in"
ALEX_TOKEN=$(login "alex.v@example.com")
info "Alex authenticated (token: ${ALEX_TOKEN:0:12}...)"

# Alex views available jobs
info "Alex views available jobs:"
authed "$ALEX_TOKEN" GET "/volunteer-calls/$CALL_ID/jobs" | pp

# Alex submits availability for both tasks
info "Alex submits availability for Task 1 (kitchen remodel):"
authed "$ALEX_TOKEN" POST "/volunteer-calls/$CALL_ID/availability" \
    -d "{
        \"person_id\": \"00000000-0000-0000-0000-000000000020\",
        \"task_id\": \"$TASK1_ID\",
        \"available\": true,
        \"max_tasks_per_week\": 2
    }" | pp

info "Alex submits availability for Task 2 (deck repair):"
authed "$ALEX_TOKEN" POST "/volunteer-calls/$CALL_ID/availability" \
    -d "{
        \"person_id\": \"00000000-0000-0000-0000-000000000020\",
        \"task_id\": \"$TASK2_ID\",
        \"available\": true,
        \"max_tasks_per_week\": 2
    }" | pp

# =============================================================================
step "7. Volunteer Beth clicks the invite link and logs in"
BETH_TOKEN=$(login "beth.h@example.com")
info "Beth authenticated (token: ${BETH_TOKEN:0:12}...)"

# Beth views jobs and volunteers for task 1 only
info "Beth submits availability for Task 1 only:"
authed "$BETH_TOKEN" POST "/volunteer-calls/$CALL_ID/availability" \
    -d "{
        \"person_id\": \"00000000-0000-0000-0000-000000000021\",
        \"task_id\": \"$TASK1_ID\",
        \"available\": true,
        \"max_tasks_per_week\": 1
    }" | pp

# =============================================================================
step "8. Admin reviews availability and assignment summary"
info "Assignment summary:"
curl -sf "$API/volunteer-calls/$CALL_ID/assignment-summary" | pp

# =============================================================================
step "9. Admin assigns volunteers to tasks"
info "Assign Alex to Task 1 (kitchen remodel):"
curl -sf "$API/volunteer-calls/$CALL_ID/tasks/$TASK1_ID/assignments" \
    -H 'Content-Type: application/json' \
    -d '{
        "person_id": "00000000-0000-0000-0000-000000000020",
        "role": "volunteer"
    }' | pp

info "Assign Beth to Task 1 (kitchen remodel):"
curl -sf "$API/volunteer-calls/$CALL_ID/tasks/$TASK1_ID/assignments" \
    -H 'Content-Type: application/json' \
    -d '{
        "person_id": "00000000-0000-0000-0000-000000000021",
        "role": "volunteer"
    }' | pp

info "Assign Alex to Task 2 (deck repair):"
curl -sf "$API/volunteer-calls/$CALL_ID/tasks/$TASK2_ID/assignments" \
    -H 'Content-Type: application/json' \
    -d '{
        "person_id": "00000000-0000-0000-0000-000000000020",
        "role": "volunteer"
    }' | pp

# =============================================================================
step "10. Admin views the assignment overview"
curl -sf "$API/volunteer-calls/$CALL_ID/assignment-overview" | pp

# =============================================================================
step "11. Admin closes the call (triggers summary notifications)"
curl -sf "$API/volunteer-calls/$CALL_ID" -X PUT -H 'Content-Type: application/json' \
    -d '{"status": "closed"}' | pp

# =============================================================================
step "12. Volunteers check their assignments"
info "Alex's assignments:"
authed "$ALEX_TOKEN" GET "/volunteering/my-assignments" | pp

info "Beth's assignments:"
authed "$BETH_TOKEN" GET "/volunteering/my-assignments" | pp

echo -e "\n${BOLD}Demo complete.${RESET}"
echo "Check console output above for email/SMS notifications sent during steps 5 and 11."
