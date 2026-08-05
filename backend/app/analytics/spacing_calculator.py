from typing import Iterable, Tuple, List
import math


def player_centroid(shots: Iterable[dict]) -> Tuple[float, float, float]:
    """Compute centroid (mean X, mean Y) and three-point density (0..1) for a player's shots.

    shots: iterable of dicts with keys 'coord_x', 'coord_y', and optional 'is_three_pointer' boolean

    Returns: (centroid_x, centroid_y, three_pt_density)
    """
    xs: List[float] = []
    ys: List[float] = []
    three_cnt = 0
    total = 0
    for s in shots:
        x = s.get("coord_x")
        y = s.get("coord_y")
        if x is None or y is None:
            continue
        try:
            xf = float(x)
            yf = float(y)
        except (TypeError, ValueError):
            continue
        xs.append(xf)
        ys.append(yf)
        if s.get("is_three_pointer"):
            three_cnt += 1
        total += 1

    if total == 0:
        return 0.0, 0.0, 0.0
    centroid_x = sum(xs) / len(xs)
    centroid_y = sum(ys) / len(ys)
    three_density = three_cnt / total
    return centroid_x, centroid_y, three_density


def overlap_percentage(shots_a: Iterable[dict], shots_b: Iterable[dict], radius: float = 2.0) -> float:
    """Compute percentage of shots in A that are within `radius` (units same as coords) of any shot in B.

    Returns value between 0 and 1.
    """
    a_points = [(s.get("coord_x"), s.get("coord_y")) for s in shots_a if s.get("coord_x") is not None and s.get("coord_y") is not None]
    b_points = [(s.get("coord_x"), s.get("coord_y")) for s in shots_b if s.get("coord_x") is not None and s.get("coord_y") is not None]

    if not a_points or not b_points:
        return 0.0

    radius2 = radius * radius
    overlapped = 0
    for ax, ay in a_points:
        for bx, by in b_points:
            dx = ax - bx
            dy = ay - by
            if dx * dx + dy * dy <= radius2:
                overlapped += 1
                break
    return overlapped / len(a_points)
