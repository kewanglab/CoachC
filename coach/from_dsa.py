"""Turn the pipeline's step 6 output into coach.py's input.

Reads <data>/projects/<you>/profiles/<kind>.json (your strokes, `guests` in dsa.measure.profiles) and
<data>/projects/<pros>/profiles/<kind>.json (the pros, `analyse`). Your value per trait is the median of your
strokes; the pro reference is the mean and SD across the pros' own medians (the box's 50th percentile).

That reference is an approximation of the article's z-scores, not their exact method, and this script has not
been run against real pipeline output yet: check the numbers it writes against the review pages before trusting them.

    python coach/from_dsa.py --data $DSA_DATA --project me --player "K" --goal "a heavier forehand" > traits.json
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

KINDS = ["forehand", "backhand", "serve"]


def stroke(mine: dict, pros: dict, player: str) -> dict | None:
    if player not in mine.get("median", {}):
        return None
    traits = {}
    for j, name in enumerate(mine["features"]):
        ref = [b[j][2] for b in pros["box"].values() if b[j][2] is not None]
        you = mine["median"][player][j]
        if you is None or len(ref) < 3:
            continue
        traits[name] = {"you": round(you, 3), "pro_mean": round(statistics.mean(ref), 3),
                        "pro_sd": round(statistics.stdev(ref), 3),
                        "unit": "torso lengths" if name in mine["lengths"] else "as measured"}
    return {"n": mine["strokes"][player], "pros": len(pros["box"]), "traits": traits}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="the pipeline's data root (DSA_DATA)")
    ap.add_argument("--project", required=True, help="your project's name in pipeline/my_project.json")
    ap.add_argument("--pros", default="atp_hardcourt")
    ap.add_argument("--player", required=True, help="your name as it appears in names.json")
    ap.add_argument("--level", default="recreational")
    ap.add_argument("--goal", default="play better tennis")
    ap.add_argument("--camera", default="phone behind the baseline")
    a = ap.parse_args()
    out = {"player": a.player, "level": a.level, "goal": a.goal, "camera": a.camera, "strokes": {}}
    for kind in KINDS:
        mine_f = a.data / "projects" / a.project / "profiles" / f"{kind}.json"
        pros_f = a.data / "projects" / a.pros / "profiles" / f"{kind}.json"
        if mine_f.exists() and pros_f.exists():
            if (s := stroke(json.loads(mine_f.read_text()), json.loads(pros_f.read_text()), a.player)):
                out["strokes"][kind] = s
    print(json.dumps(out, indent=1))
