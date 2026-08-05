from app.analytics.spacing_calculator import player_centroid, overlap_percentage
from app.analytics.clutch_analyzer import compute_clutch_ts
from app.analytics.chemistry_engine import compose_report


def test_player_centroid_and_three_density():
    shots = [
        {"coord_x": 0.0, "coord_y": 0.0, "is_three_pointer": False},
        {"coord_x": 2.0, "coord_y": 0.0, "is_three_pointer": True},
        {"coord_x": 0.0, "coord_y": 2.0, "is_three_pointer": False},
    ]
    cx, cy, three_density = player_centroid(shots)
    assert round(cx, 2) == round((0 + 2 + 0) / 3, 2)
    assert round(cy, 2) == round((0 + 0 + 2) / 3, 2)
    assert three_density == 1 / 3


def test_overlap_percentage():
    a = [{"coord_x": 0.0, "coord_y": 0.0}, {"coord_x": 10.0, "coord_y": 10.0}]
    b = [{"coord_x": 0.5, "coord_y": 0.5}]
    ov = overlap_percentage(a, b, radius=1.0)
    # only first of A is within 1.0 distance of B
    assert ov == 0.5


def test_compute_clutch_ts_simple():
    events = [
        {"quarter": 4, "time_remaining": 120, "score_diff": 2, "event_type": "shot", "points": 2, "made": True},
        {"quarter": 4, "time_remaining": 60, "score_diff": -1, "event_type": "shot", "points": 3, "made": False},
        {"quarter": 4, "time_remaining": 30, "score_diff": 0, "event_type": "ft", "is_ft": True, "points": 1, "made": True},
    ]
    ts = compute_clutch_ts(events)
    # points = 2 + 1 = 3 ; FGA = 2 ; FTA = 1 -> denom = 2*(2 + 0.44*1)=2*(2.44)=4.88 -> TS = 3/4.88*100 ~ 61.47
    assert round(ts, 0) == 61


def test_compose_report_basic():
    starters = []
    for i in range(5):
        starters.append({
            "player_code": f"s{i}",
            "shots": [{"coord_x": i * 2.0, "coord_y": 0.0, "is_three_pointer": False, "zone": "Zone"} for _ in range(5)]
        })
    recruit = {"player_code": "r1", "shots": [{"coord_x": 0.0, "coord_y": 0.0, "is_three_pointer": False, "zone": "Zone"}]}
    play_by_play = [
        {"quarter": 4, "time_remaining": 30, "score_diff": 1, "player_code": "s0", "event_type": "shot", "points": 2, "made": True}
    ]
    report = compose_report(starters, recruit, play_by_play)
    assert "spacing_score" in report
    assert "clutch_score" in report
    assert isinstance(report.get("conflicts"), list)
