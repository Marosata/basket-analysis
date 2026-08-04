from typing import Optional, Callable, Tuple
import time

from app.services.data_fetcher import EuroleagueDataFetcher
from app.models.shot import ShotListResponse
from app.models.player import PlayerStatsListResponse

# Simple in-memory TTL cache. Key -> (expiry_timestamp, value)
_CACHE: dict[str, Tuple[float, object]] = {}
# Default TTL seconds
DEFAULT_TTL = 300  # 5 minutes


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    parts = [prefix] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return "|".join(parts)


def _get_cached(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None
    expiry, value = entry
    if time.time() > expiry:
        # expired
        _CACHE.pop(key, None)
        return None
    return value


def _set_cache(key: str, value: object, ttl: int = DEFAULT_TTL):
    _CACHE[key] = (time.time() + ttl, value)


def _validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    # enforce sensible defaults and bounds
    if page is None or page < 1:
        page = 1
    if page_size is None or page_size < 1:
        # 0 indicates return all; but default we'll set large value
        page_size = 1000
    # cap page_size to avoid huge responses
    page_size = min(page_size, 5000)
    return page, page_size


def _paginate_list(items: list, page: int, page_size: int) -> list:
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


def get_shots_service(
    season: int,
    game_code: Optional[int],
    fetcher: EuroleagueDataFetcher,
    ttl: int = DEFAULT_TTL,
    page: int = 1,
    page_size: int = 1000,
) -> ShotListResponse:
    """Return shots for a given game or entire season with pagination.

    Uses in-memory TTL cache for full-query results (unpaginated total list),
    then slices the list for the requested page. Cache key does not include
    pagination so different pages share the same cached full data.
    """
    key = _make_cache_key("shots", season, game_code)
    cached = _get_cached(key)
    if cached is None:
        if game_code is not None:
            shots = fetcher.fetch_game_shots(season, game_code)
        else:
            shots = fetcher.fetch_season_shots(season)
        _set_cache(key, shots, ttl=ttl)
    else:
        shots = cached

    total = len(shots)
    page, page_size = _validate_pagination(page, page_size)
    paged = _paginate_list(shots, page, page_size)

    response = ShotListResponse(total=total, page=page, page_size=page_size, shots=paged)
    return response


def get_player_stats_service(
    season: int,
    endpoint: str,
    stat_mode: str,
    fetcher: EuroleagueDataFetcher,
    ttl: int = DEFAULT_TTL,
    page: int = 1,
    page_size: int = 1000,
) -> PlayerStatsListResponse:
    """Return player statistics for a season with pagination.

    Cache stores the full players list; responses slice it per page.
    """
    key = _make_cache_key("players", season, endpoint, stat_mode)
    cached = _get_cached(key)
    if cached is None:
        players = fetcher.fetch_player_stats(season=season, endpoint=endpoint, stat_mode=stat_mode)
        _set_cache(key, players, ttl=ttl)
    else:
        players = cached

    total = len(players)
    page, page_size = _validate_pagination(page, page_size)
    paged = _paginate_list(players, page, page_size)

    response = PlayerStatsListResponse(total=total, page=page, page_size=page_size, players=paged)
    return response


# Expose a helper for tests to clear cache
def _clear_cache():
    _CACHE.clear()


# Simple decorator for caching service functions if needed later
def ttl_cache(ttl: int = DEFAULT_TTL):
    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            key = _make_cache_key(fn.__name__, *args, **kwargs)
            cached = _get_cached(key)
            if cached is not None:
                return cached
            res = fn(*args, **kwargs)
            _set_cache(key, res, ttl=ttl)
            return res

        return wrapper

    return decorator
