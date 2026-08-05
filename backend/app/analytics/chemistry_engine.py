from typing import List, Dict, Any

from app.analytics.spacing_calculator import player_centroid, overlap_percentage
from app.analytics.clutch_analyzer import compute_clutch_ts


def compute_spacing_score(starters: List[Dict[str, Any]], recruit: Dict[str, Any]) -> float:
    """Compute a simple spacing score for the five starters plus recruit.

    Strategy:
    - compute centroids for each starter, then compute average pairwise distance
      between the 5 starters centroids; higher mean distance -> better spacing.
    - penalize overlap between recruit and starters (sum of overlaps)

    Returns a normalized score (0..100)
    """
    centroids = []
    for p in starters:
        cx, cy, _ = player_centroid(p.get("shots", []))
        centroids.append((cx, cy))

    # compute mean pairwise distance among starters
    n = len(centroids)
    if n < 2:
        mean_pair_dist = 0.0
    else:
        total = 0.0
        count = 0
        for i in range(n):
            xi, yi = centroids[i]
            for j in range(i + 1, n):
                xj, yj = centroids[j]
                dx = xi - xj
                dy = yi - yj
                total += (dx * dx + dy * dy) ** 0.5
                count += 1
        mean_pair_dist = total / count if count else 0.0

    # recruit overlap penalty
    overlap_sum = 0.0
    for p in starters:
        ov = overlap_percentage(p.get("shots", []), recruit.get("shots", []))
        overlap_sum += ov

    # produce score: normalize mean_pair_dist (assume court coords roughly within ~ [-25,25])
    normalized_spacing = min(max(mean_pair_dist / 20.0, 0.0), 1.0)
    overlap_penalty = min(max(overlap_sum / max(1, len(starters)), 0.0), 1.0)

    # spacing score in 0..100 where overlap reduces score
    score = (normalized_spacing * 100.0) * (1.0 - overlap_penalty)
    return round(score, 2)


def compute_clutch_score(play_by_play: List[Dict[str, Any]], starters: List[Dict[str, Any]]) -> float:
    """Compute team-level clutch score as average TS% across starters based on provided play_by_play events.
    If play_by_play is empty, fallback to 0.0
    """
    if not play_by_play:
        return 0.0
    # Assume events contain a 'player_code' to map to starters
    scores = []
    for p in starters:
        player_events = [e for e in play_by_play if e.get("player_code") == p.get("player_code")]
        ts = compute_clutch_ts(player_events)
        scores.append(ts)
    if not scores:
        return 0.0
    # average
    return round(sum(scores) / len(scores), 2)


def detect_conflicts(starters: List[Dict[str, Any]], recruit: Dict[str, Any], overlap_threshold: float = 0.2) -> List[Dict[str, Any]]:
    """Return list of conflict zones: for each starter with overlap > threshold, return player_code and overlap and top zones of conflict.
    Zones are taken from shot 'zone' attribute; we return top 2 zones where shots overlap by proximity.
    """
    conflicts = []
    for p in starters:
        ov = overlap_percentage(p.get("shots", []), recruit.get("shots", []))
        if ov > overlap_threshold:
            # compute top zones in p shots that are close to recruit shots
            zones = []
            # collect shots of p that are within small radius of any recruit shot
            from app.analytics.spacing_calculator import overlap_percentage as _ovf

            # we'll compute zones frequency simply by checking proximity of points
            p_shots = [s for s in p.get("shots", []) if s.get("zone")]
            r_shots = [s for s in recruit.get("shots", []) if s.get("zone")]
            zone_counts = {}
            radius = 2.0
            for ps in p_shots:
                for rs in r_shots:
                    dx = ps.get("coord_x") - rs.get("coord_x")
                    dy = ps.get("coord_y") - rs.get("coord_y")
                    if dx * dx + dy * dy <= radius * radius:
                        z = ps.get("zone")
                        zone_counts[z] = zone_counts.get(z, 0) + 1
                        break
            # top zones
            sorted_z = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)
            top_z = [z for z, _ in sorted_z[:2]]
            conflicts.append({"player_code": p.get("player_code"), "overlap": round(ov, 3), "zones": top_z})
    return conflicts


def compose_report(starters: List[Dict[str, Any]], recruit: Dict[str, Any], play_by_play: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    spacing_score = compute_spacing_score(starters, recruit)
    clutch_score = compute_clutch_score(play_by_play or [], starters)
    conflicts = detect_conflicts(starters, recruit)
    return {"spacing_score": spacing_score, "clutch_score": clutch_score, "conflicts": conflicts}
