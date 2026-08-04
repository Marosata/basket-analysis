from pydantic import BaseModel, Field


class Shot(BaseModel):
    season: int
    game_code: int
    player_code: str
    team_code: str
    coord_x: float | None = None
    coord_y: float | None = None
    action_id: str
    action_label: str | None = None
    zone: str | None = None
    is_made: bool
    is_three_pointer: bool


class ShotListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 0
    shots: list[Shot] = Field(default_factory=list)
