import time

from app.services.ingestion_service import get_shots_service, get_player_stats_service, _clear_cache
from app.models.shot import Shot
from app.models.player import PlayerStats


class DummyFetcher:
    def __init__(self):
        self.game_shots_called = 0
        self.season_shots_called = 0
        self.player_stats_called = 0

    def fetch_game_shots(self, season, game_code):
        self.game_shots_called += 1
        # return a list of one Shot
        return [
            Shot(
                season=season,
                game_code=game_code,
                player_code="p1",
                team_code="t1",
                coord_x=10.0,
                coord_y=20.0,
                action_id="2FGM",
                action_label="2pt Made",
                zone="Paint",
                is_made=True,
                is_three_pointer=False,
            )
        ]

    def fetch_season_shots(self, season):
        self.season_shots_called += 1
        return [
            Shot(
                season=season,
                game_code=1,
                player_code="p1",
                team_code="t1",
                coord_x=11.0,
                coord_y=21.0,
                action_id="3FGM",
                action_label="3pt Made",
                zone="Corner",
                is_made=True,
                is_three_pointer=True,
            )
        ]

    def fetch_player_stats(self, season, endpoint, stat_mode):
        self.player_stats_called += 1
        return [
            PlayerStats(
                player_code="p1",
                player_name="Player One",
                team_code="t1",
                position="G",
                season=season,
                games_played=10,
                points=12.3,
                rebounds=4.5,
                assists=3.2,
                steals=1.0,
                blocks=0.5,
                turnovers=2.1,
                fg_pct=45.6,
                three_pt_pct=38.2,
                ft_pct=80.0,
                minutes_played=25.0,
            )
        ]


def test_shots_cache_behavior():
    _clear_cache()
    f = DummyFetcher()
    # first call should hit fetcher
    res1 = get_shots_service(season=2024, game_code=1001, fetcher=f, ttl=2)
    assert res1.total == 1
    assert f.game_shots_called == 1

    # second call immediately should be from cache
    res2 = get_shots_service(season=2024, game_code=1001, fetcher=f, ttl=2)
    assert res2.total == 1
    assert f.game_shots_called == 1

    # wait for cache expiry
    time.sleep(2.1)
    res3 = get_shots_service(season=2024, game_code=1001, fetcher=f, ttl=2)
    assert res3.total == 1
    assert f.game_shots_called == 2


def test_season_shots_and_player_stats_cache():
    _clear_cache()
    f = DummyFetcher()
    # season shots
    s1 = get_shots_service(season=2024, game_code=None, fetcher=f, ttl=60)
    assert s1.total == 1
    assert f.season_shots_called == 1

    s2 = get_shots_service(season=2024, game_code=None, fetcher=f, ttl=60)
    assert f.season_shots_called == 1

    # player stats
    p1 = get_player_stats_service(season=2024, endpoint="traditional", stat_mode="PerGame", fetcher=f, ttl=60)
    assert p1.total == 1
    assert f.player_stats_called == 1

    p2 = get_player_stats_service(season=2024, endpoint="traditional", stat_mode="PerGame", fetcher=f, ttl=60)
    assert f.player_stats_called == 1


def test_pagination_shots():
    _clear_cache()

    class LargeFetcher(DummyFetcher):
        def fetch_season_shots(self, season):
            # return 50 shot objects
            shots = []
            for i in range(50):
                shots.append(
                    Shot(
                        season=season,
                        game_code=i,
                        player_code=f"p{i}",
                        team_code="t1",
                        coord_x=float(i),
                        coord_y=float(i + 0.5),
                        action_id="2FGM",
                        action_label="2pt Made",
                        zone="Zone",
                        is_made=True,
                        is_three_pointer=False,
                    )
                )
            self.season_shots_called += 1
            return shots

    f = LargeFetcher()
    # request page 2, page_size 10 -> items 10..19
    res = get_shots_service(season=2024, game_code=None, fetcher=f, ttl=60, page=2, page_size=10)
    assert res.total == 50
    assert res.page == 2
    assert res.page_size == 10
    assert len(res.shots) == 10
    assert res.shots[0].game_code == 10
