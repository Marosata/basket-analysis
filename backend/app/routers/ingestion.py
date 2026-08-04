from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.models.player import PlayerStatsListResponse
from app.models.shot import ShotListResponse
from app.services.data_fetcher import EuroleagueDataFetcher
from app.services.ingestion_service import get_shots_service, get_player_stats_service

router = APIRouter(tags=["ingestion"])

StatEndpoint = Literal["traditional", "advanced", "misc", "scoring"]
StatMode = Literal[
    "PerGame",
    "Accumulated",
    "PerMinute",
    "Per100Possesions",
    "PerGameReverse",
    "AccumulatedReverse",
]


def get_data_fetcher() -> EuroleagueDataFetcher:
    return EuroleagueDataFetcher(competition_code=settings.competition_code)


@router.get("/shots", response_model=ShotListResponse)
def get_shots(
    season: int = Query(..., description="Année de début de saison (ex: 2024 pour E2024)"),
    game_code: int | None = Query(
        default=None,
        description="Code du match. Si absent, retourne tous les tirs de la saison.",
    ),
    page: int = Query(1, description="Page number (1-based)"),
    page_size: int = Query(1000, description="Page size (max 5000)"),
    fetcher: EuroleagueDataFetcher = Depends(get_data_fetcher),
) -> ShotListResponse:
    return get_shots_service(season=season, game_code=game_code, fetcher=fetcher, page=page, page_size=page_size)


@router.get("/players/stats", response_model=PlayerStatsListResponse)
def get_player_stats(
    season: int = Query(..., description="Année de début de saison (ex: 2024 pour E2024)"),
    endpoint: StatEndpoint = Query(
        default="traditional",
        description="Type de statistiques joueur",
    ),
    stat_mode: StatMode = Query(
        default="PerGame",
        description="Mode d'agrégation des statistiques",
    ),
    page: int = Query(1, description="Page number (1-based)"),
    page_size: int = Query(1000, description="Page size (max 5000)"),
    fetcher: EuroleagueDataFetcher = Depends(get_data_fetcher),
) -> PlayerStatsListResponse:
    return get_player_stats_service(season=season, endpoint=endpoint, stat_mode=stat_mode, fetcher=fetcher, page=page, page_size=page_size)
