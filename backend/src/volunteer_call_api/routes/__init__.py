"""API routes for volunteer call system."""

from fastapi import APIRouter, Depends

from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.routes.auth import router as auth_router
from volunteer_call_api.routes.notifications import router as notifications_router
from volunteer_call_api.routes.people import router as people_router
from volunteer_call_api.routes.reports import router as reports_router
from volunteer_call_api.routes.team_assignments import router as team_assignments_router
from volunteer_call_api.routes.volunteer_availability import router as volunteer_availability_router
from volunteer_call_api.routes.volunteer_calls import router as volunteer_calls_router
from volunteer_call_api.routes.volunteering import router as volunteering_router

api_router = APIRouter()

# Auth routes — no token required
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# All other routes require Bearer token auth
authenticated = APIRouter(dependencies=[Depends(get_current_user)])
authenticated.include_router(people_router, prefix="/people", tags=["people"])
authenticated.include_router(
    volunteer_calls_router, prefix="/volunteer-calls", tags=["volunteer-calls"]
)
authenticated.include_router(
    volunteer_availability_router, prefix="/volunteer-calls", tags=["availability"]
)
authenticated.include_router(
    team_assignments_router, prefix="/volunteer-calls", tags=["team-assignments"]
)
authenticated.include_router(reports_router, prefix="/reports", tags=["reports"])
authenticated.include_router(volunteering_router, prefix="/volunteering", tags=["volunteering"])
authenticated.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

api_router.include_router(authenticated)
