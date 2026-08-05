from fastapi import APIRouter, HTTPException
from app.models.analytics import SimulationRequest, SimulationResponse
from app.analytics.chemistry_engine import compose_report

router = APIRouter(tags=["analytics"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest) -> SimulationResponse:
    # Basic validation: starters must be 5
    if not request.starters or len(request.starters) != 5:
        raise HTTPException(status_code=400, detail="'starters' must contain exactly 5 players")

    report = compose_report(
        starters=[s.dict() for s in request.starters],
        recruit=request.recruit.dict(),
        play_by_play=request.play_by_play or [],
    )
    return SimulationResponse(**report)
