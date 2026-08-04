from pydantic import BaseModel, Field


class Player(BaseModel):
    player_code: str
    player_name: str
    team_code: str
    position: str | None = None


class PlayerStats(Player):
    season: int
    games_played: int | None = None
    points: float | None = None
    rebounds: float | None = None
    assists: float | None = None
    steals: float | None = None
    blocks: float | None = None
    turnovers: float | None = None
    fg_pct: float | None = None
    three_pt_pct: float | None = None
    ft_pct: float | None = None
    minutes_played: float | None = None


class PlayerStatsListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 0
    players: list[PlayerStats] = Field(default_factory=list)
