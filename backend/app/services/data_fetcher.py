import math
import time
from json.decoder import JSONDecodeError

import pandas as pd
import requests
from euroleague_api.player_stats import PlayerStats
from euroleague_api.shot_data import ShotData

from app.models.player import PlayerStats as PlayerStatsModel
from app.models.shot import Shot

MADE_ACTIONS = {"2FGM", "3FGM", "LAYUPMD", "DUNK", "FTM"}


class DataNotFoundError(Exception):
    pass


class UpstreamAPIError(Exception):
    pass


def _parse_percentage(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_optional_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _to_optional_int(value: object) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return int(value)


def _is_made(action_id: str) -> bool:
    return action_id in MADE_ACTIONS


def _is_three_pointer(action_id: str) -> bool:
    return action_id.startswith("3FG")


def _normalize_shot_row(row: pd.Series) -> Shot | None:
    coord_x = _to_optional_float(row.get("COORD_X"))
    coord_y = _to_optional_float(row.get("COORD_Y"))
    if coord_x is None or coord_y is None:
        return None

    action_id = str(row.get("ID_ACTION", "")).strip()
    if not action_id:
        return None

    zone = row.get("ZONE")
    zone_value = None if pd.isna(zone) else str(zone).strip()

    action_label = row.get("ACTION")
    action_label_value = None if pd.isna(action_label) else str(action_label).strip()

    return Shot(
        season=int(row["Season"]),
        game_code=int(row["Gamecode"]),
        player_code=str(row.get("ID_PLAYER", "")).strip(),
        team_code=str(row.get("TEAM", "")).strip(),
        coord_x=coord_x,
        coord_y=coord_y,
        action_id=action_id,
        action_label=action_label_value,
        zone=zone_value,
        is_made=_is_made(action_id),
        is_three_pointer=_is_three_pointer(action_id),
    )


def _normalize_player_row(row: pd.Series, season: int) -> PlayerStatsModel:
    two_made = _to_optional_float(row.get("twoPointersMade")) or 0.0
    three_made = _to_optional_float(row.get("threePointersMade")) or 0.0
    two_attempted = _to_optional_float(row.get("twoPointersAttempted")) or 0.0
    three_attempted = _to_optional_float(row.get("threePointersAttempted")) or 0.0

    fg_attempted = two_attempted + three_attempted
    fg_pct = None
    if fg_attempted > 0:
        fg_pct = round((two_made + three_made) / fg_attempted * 100, 1)

    return PlayerStatsModel(
        player_code=str(row.get("player.code", "")).strip(),
        player_name=str(row.get("player.name", "")).strip(),
        team_code=str(row.get("player.team.code", "")).strip(),
        position=None,
        season=season,
        games_played=_to_optional_int(row.get("gamesPlayed")),
        points=_to_optional_float(row.get("pointsScored")),
        rebounds=_to_optional_float(row.get("totalRebounds")),
        assists=_to_optional_float(row.get("assists")),
        steals=_to_optional_float(row.get("steals")),
        blocks=_to_optional_float(row.get("blocks")),
        turnovers=_to_optional_float(row.get("turnovers")),
        fg_pct=fg_pct,
        three_pt_pct=_parse_percentage(row.get("threePointersPercentage")),
        ft_pct=_parse_percentage(row.get("freeThrowsPercentage")),
        minutes_played=_to_optional_float(row.get("minutesPlayed")),
    )


class EuroleagueDataFetcher:
    def __init__(self, competition_code: str = "E") -> None:
        self.competition_code = competition_code
        # Initialize clients provided by euroleague_api
        self._shot_data = ShotData(competition_code)
        self._player_stats = PlayerStats(competition_code)

    def _call_with_retries(self, func, *args, retries: int = 2, backoff: float = 0.5, **kwargs):
        last_exc = None
        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(backoff * (1 + attempt))
            except JSONDecodeError as exc:
                # upstream returned invalid JSON
                raise UpstreamAPIError("Invalid JSON response from upstream API") from exc
            except Exception as exc:
                # Non-network exception from upstream client
                last_exc = exc
                time.sleep(backoff * (1 + attempt))
        raise UpstreamAPIError(str(last_exc)) from last_exc

    def fetch_game_shots(self, season: int, game_code: int) -> list[Shot]:
        # Call known method names, be permissive if upstream changes method name
        candidates = [
            (self._shot_data, "get_game_shot_data"),
            (self._shot_data, "get_game_shotdata"),
        ]
        df = None
        for obj, method in candidates:
            if hasattr(obj, method):
                func = getattr(obj, method)
                try:
                    df = self._call_with_retries(func, season, game_code)
                    break
                except UpstreamAPIError:
                    raise
                except Exception as exc:
                    # try next candidate
                    last_exc = exc
                    continue

        if df is None:
            raise UpstreamAPIError(
                f"No usable shot-data method found on euroleague client for season={season}, game_code={game_code}"
            )

        if df.empty:
            raise DataNotFoundError(
                f"No shot data found for season={season}, game_code={game_code}"
            )

        return self._dataframe_to_shots(df)

    def fetch_season_shots(self, season: int) -> list[Shot]:
        # Some versions offer get_game_shot_data_single_season, others different name
        candidates = [
            (self._shot_data, "get_game_shot_data_single_season"),
            (self._shot_data, "get_season_shot_data"),
            (self._shot_data, "get_game_shotdata_single_season"),
        ]
        df = None
        for obj, method in candidates:
            if hasattr(obj, method):
                func = getattr(obj, method)
                try:
                    df = self._call_with_retries(func, season)
                    break
                except UpstreamAPIError:
                    raise
                except Exception:
                    continue

        if df is None:
            raise UpstreamAPIError(f"No usable season-shot method found for season={season}")

        if df.empty:
            raise DataNotFoundError(f"No shot data found for season={season}")

        return self._dataframe_to_shots(df)

    def fetch_player_stats(
        self,
        season: int,
        endpoint: str = "traditional",
        stat_mode: str = "PerGame",
    ) -> list[PlayerStatsModel]:
        # Candidate method names for backward compatibility
        candidates = [
            (self._player_stats, "get_player_stats_single_season"),
            (self._player_stats, "get_player_stats"),
        ]
        df = None
        for obj, method in candidates:
            if hasattr(obj, method):
                func = getattr(obj, method)
                try:
                    # try calling with keyword args, fall back to positional if needed
                    try:
                        df = self._call_with_retries(
                            func, endpoint=endpoint, season=season, statistic_mode=stat_mode
                        )
                    except TypeError:
                        df = self._call_with_retries(func, season, endpoint, stat_mode)
                    break
                except ValueError as exc:
                    raise DataNotFoundError(str(exc)) from exc
                except UpstreamAPIError:
                    raise
                except Exception:
                    continue

        if df is None:
            raise UpstreamAPIError(f"No usable player-stats method found for season={season}")

        if df.empty:
            raise DataNotFoundError(
                f"No player stats found for season={season}, endpoint={endpoint}"
            )

        return [_normalize_player_row(row, season) for _, row in df.iterrows()]

    @staticmethod
    def _dataframe_to_shots(df: pd.DataFrame) -> list[Shot]:
        shots: list[Shot] = []
        for _, row in df.iterrows():
            shot = _normalize_shot_row(row)
            if shot is not None:
                shots.append(shot)
        return shots
