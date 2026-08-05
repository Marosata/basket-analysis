from typing import Iterable, Dict, Any

# We'll compute True Shooting % (TS%) for clutch situations.
# TS% = Points / (2*(FGA + 0.44*FTA))
# Input events: iterable of dicts with keys:
#  - 'quarter' (int)
#  - 'time_remaining' (seconds remaining in quarter) or 'game_minute' optional
#  - 'score_diff' (team_score - opp_score), positive means team ahead
#  - 'event_type' : 'shot' | 'ft' | ...
#  - 'points' : attempted shot value (2 or 3) for shots, 1 for FT
#  - 'made' : boolean for shot/ft
#  - 'is_ft' : boolean true for free-throw attempts (counts in FTA)


def compute_clutch_ts(events: Iterable[Dict[str, Any]], last_seconds: int = 300, margin: int = 5) -> float:
    """Compute True Shooting % for events that occur in the last_seconds of the 4th quarter
    and where abs(score_diff) <= margin.

    Returns TS% as a 0..100 float. If no qualifying attempts, returns 0.0
    """
    fga = 0
    fta = 0
    points = 0

    for ev in events:
        try:
            quarter = int(ev.get("quarter", 0))
        except (TypeError, ValueError):
            continue
        if quarter != 4:
            continue
        remaining = ev.get("time_remaining")
        # if time provided as mm:ss string, caller should pre-process; we expect seconds
        if remaining is None:
            continue
        try:
            remaining = float(remaining)
        except (TypeError, ValueError):
            continue
        if remaining > last_seconds:
            continue
        score_diff = ev.get("score_diff")
        if score_diff is None:
            continue
        try:
            sd = float(score_diff)
        except (TypeError, ValueError):
            continue
        if abs(sd) > margin:
            continue

        # now this event is in clutch window
        if ev.get("is_ft"):
            fta += 1
            if ev.get("made"):
                points += float(ev.get("points", 1))
        elif ev.get("event_type") == "shot":
            fga += 1
            if ev.get("made"):
                points += float(ev.get("points", 0))
        # other event types ignored for TS calc

    denominator = 2 * (fga + 0.44 * fta)
    if denominator <= 0:
        return 0.0
    ts = points / denominator * 100.0
    return round(ts, 2)
