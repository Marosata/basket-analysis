from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ShotInput(BaseModel):
    coord_x: float
    coord_y: float
    is_three_pointer: Optional[bool] = False
    zone: Optional[str] = None


class PlayerShots(BaseModel):
    player_code: str
    shots: List[ShotInput] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    starters: List[PlayerShots]
    recruit: PlayerShots
    play_by_play: Optional[List[dict]] = None


class ConflictOut(BaseModel):
    player_code: str
    overlap: float
    zones: List[str] = Field(default_factory=list)


class SimulationResponse(BaseModel):
    spacing_score: float
    clutch_score: float
    conflicts: List[ConflictOut] = Field(default_factory=list)
