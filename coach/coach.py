"""Ask Claude what to fix, from your stroke traits measured against a pro reference.

The article's coaching step, on its own: every trait becomes a z-score against the pros, and Claude gets all of
them in a fresh session (no memory) with the setting and the goal, not a checklist, and returns a ranked list of
fixes. Works with traits from the full pipeline (coach/from_dsa.py) or ones you measured yourself.

    uv run python coach/coach.py coach/example_traits.json            -> prints the fixes, writes <input>.fixes.json
    uv run python coach/coach.py traits.json --effort high

Input (JSON):
    {"player": "K", "level": "4.0 club player", "goal": "a heavier forehand", "camera": "phone behind the baseline",
     "strokes": {"forehand": {"n": 24, "traits": {"<trait>": {"you": 0.8, "pro_mean": 1.1, "pro_sd": 0.2,
                                                             "unit": "torso lengths"}}}}}

Auth: ANTHROPIC_API_KEY (or an `ant auth login` profile).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "fixes", "refilm_check"],
    "properties": {
        "summary": {"type": "string"},
        "fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["rank", "stroke", "fix", "why", "traits", "drill", "confidence"],
                "properties": {
                    "rank": {"type": "integer"},
                    "stroke": {"type": "string"},
                    "fix": {"type": "string"},
                    "why": {"type": "string"},
                    "traits": {"type": "array", "items": {"type": "string"}},
                    "drill": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "refilm_check": {"type": "string"},
    },
}


def z_scores(data: dict) -> dict:
    """The input with a z-score on every trait that has a pro spread; others are left as they are."""
    for stroke in data["strokes"].values():
        for t in stroke["traits"].values():
            if t.get("pro_sd"):
                t["z"] = round((t["you"] - t["pro_mean"]) / t["pro_sd"], 2)
    return data


def prompt(data: dict) -> str:
    # setting and goal, not steps: the article found Claude coached better this way
    return f"""You are coaching {data.get("player", "a recreational tennis player")} ({data.get("level", "level unknown")}).

Their strokes were filmed ({data.get("camera", "camera unknown")}), and a pose pipeline measured traits per stroke.
Lengths are in torso lengths, so body size is factored out. Each trait carries the player's value, the pros' mean
and spread, and a z-score against the pros. A large z is a difference, not necessarily a fault: some differences
are style, and some are camera error (a low camera foreshortens anything pointing toward the net). n is how many
strokes the numbers come from.

Their goal: {data.get("goal", "play better tennis")}.

Decide what they should work on. Rank the fixes by how much each would help the goal, give the traits behind each,
one drill, and how confident the numbers let you be. Keep it to the few things worth a month of practice. Say what
to check when they film again in a few weeks.

The measurements:
{json.dumps(data["strokes"], indent=1)}"""


def ask(data: dict, effort: str) -> dict:
    client = anthropic.Anthropic()
    with client.beta.messages.stream(
            model=MODEL, max_tokens=64000,
            thinking={"type": "adaptive"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",   # a declined request reruns server-side
            messages=[{"role": "user", "content": prompt(data)}]) as stream:
        r = stream.get_final_message()
    if r.stop_reason == "refusal":
        raise SystemExit(f"declined: {r.stop_details}")
    return json.loads("".join(b.text for b in r.content if b.type == "text"))


def show(fixes: dict) -> None:
    print(fixes["summary"], "\n")
    for f in sorted(fixes["fixes"], key=lambda f: f["rank"]):
        print(f"{f['rank']}. [{f['stroke']}] {f['fix']}  ({f['confidence']} confidence)")
        print(f"   why:   {f['why']}")
        print(f"   from:  {', '.join(f['traits'])}")
        print(f"   drill: {f['drill']}\n")
    print("When you re-film:", fixes["refilm_check"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("traits", type=Path)
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--dry-run", action="store_true", help="print the prompt, call nothing")
    a = ap.parse_args()
    data = z_scores(json.loads(a.traits.read_text()))
    if a.dry_run:
        print(prompt(data))
        raise SystemExit
    fixes = ask(data, a.effort)
    a.traits.with_suffix(".fixes.json").write_text(json.dumps(fixes, indent=1))
    show(fixes)
