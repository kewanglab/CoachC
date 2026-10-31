# CoachC

Claude as a tennis coach, set up for my own footage. Based on
[Claude as a Tennis Coach](https://offpolicyinc.com/work/claude-tennis-coach/) (Peter Wang and Nico Christie,
Off Policy, October 22, 2026) and its code, [offpolicyinc/deep-sports-analysis](https://github.com/offpolicyinc/deep-sports-analysis) (MIT).

**The idea:** pose-track your strokes, measure about 55 traits per stroke (lengths in torso lengths), turn each
into a z-score against 11 ATP pros, and give Claude all the numbers in a fresh session to rank what to fix.

```
upstream/deep-sports-analysis/   the Off Policy pipeline, a git submodule pinned at 2d742ad (Oct 27, 2026)
pipeline/my_project.json         my footage as a pipeline project (read through DSA_PROJECTS; no upstream edits)
coach/coach.py                   the coaching step: traits -> z-scores -> Claude -> ranked fixes
coach/from_dsa.py                pipeline output (step 6) -> coach.py input
coach/example_traits.json        MADE-UP numbers, for testing the format only
```

## Two ways to use it

### A. Light path: your numbers + Claude (start here)

No GPUs. Measure a few traits yourself (from a pose model, or by hand from video frames), add a pro reference
range for each, and run:

```
uv sync
cp .env.example .env            # set ANTHROPIC_API_KEY
uv run python coach/coach.py coach/example_traits.json --dry-run    # see the prompt, no call
uv run python coach/coach.py my_traits.json                          # ranked fixes, also saved as my_traits.fixes.json
```

The pro ranges are the hard part. Don't make them up: take them from the pipeline (path B), a published source,
or leave a trait without `pro_sd` and Claude sees the raw value only. A forked project,
[amattapalli/tennis-vision](https://github.com/amattapalli/tennis-vision), adapts the stack to a fence-mounted
phone, and there's a simpler [MediaPipe + Claude build on Medium](https://gauravsarma1992.medium.com/building-an-ai-tennis-coach-with-mediapipe-and-claude-4d791a2dd278).

### B. Full pipeline on your footage

```
git submodule update --init
cd upstream/deep-sports-analysis && uv sync --extra cloud     # Modal client; GPU steps never run locally
modal setup                                                    # Modal account
export DSA_DATA=/path/to/data DSA_PROJECTS=$PWD/../../pipeline/my_project.json ANTHROPIC_API_KEY=...
```

Then follow upstream [docs/PIPELINE.md](upstream/deep-sports-analysis/docs/PIPELINE.md) (Commands) for
`me/<video>`: models on Modal (step 2), players (3), names (4: set by hand for amateurs, as upstream does for
its own sessions), measurements (5), compare (6). Then:

```
uv run python coach/from_dsa.py --data $DSA_DATA --project me --player K --goal "a heavier forehand" > traits.json
uv run python coach/coach.py traits.json
```

Edit `pipeline/my_project.json` first: your name, your partner's, the video path and start/length in seconds.
Heights are in meters, as upstream expects (5'9" = 1.75).

**What to expect before committing to path B:**

- **The pro reference isn't included.** The repo ships code, not the ATP numbers. Comparing against pros means
  running the `atp_hardcourt` project yourself: downloading many broadcast matches from YouTube and putting
  them through the GPU steps. That's the main cost and effort, not your own footage.
- **Model weights are manual.** The weights for WASB, TennisCourtDetector, F3ED, and RF-DETR go under
  `$DSA_DATA/models` and `code/` and get pushed to a Modal volume (`dsa.gpu.volume.push`; layout in
  [docs/STORAGE.md](upstream/deep-sports-analysis/docs/STORAGE.md)). No setup script fetches them.
- **GPU cost** (upstream's measurements): about $0.037 per minute of play on an L40S for step 2, about $2.20 per
  26-minute broadcast video. Check `modal billing report --for today`.
- **Upstream's own reference data is on their laptop.** Paths like `data/raw/...` and the GCP project in
  `dsa.gpu.gcp` are theirs. Use Modal, not the GCP route.

## Filming

- Shoot from **behind the baseline**, centered, as high as you can (fence-mounted or a tall tripod). Their phone
  footage came from there, and the low angle cost them **seven traits**, including hip turn, contact height, and
  serve reach. A low camera can't see anything pointing toward the net well.
- Film at 30 fps, 1080p, as upstream's own sessions were. F3ED (stroke labels) misses most hits at 50/60 fps.
- Film enough: in upstream's notes, 20 minutes of play gave 10–15 routine near-end forehands per player but only
  2–5 backhands and serves. You're measured only at the **near end**.

## Prompting lesson (built into coach.py)

Give Claude the setting and the goal, not step-by-step instructions. Ask it to rank fixes, keep the list short,
and say what to check on the next session. Re-film after a few weeks and run it again.
In the article, Claude also watched clips to refine one stroke. That part isn't included here.

## Notes and corrections

- **Auth is `ANTHROPIC_API_KEY`, not `CLAUDE_CODE_OAUTH_TOKEN`.** The repo's court-marking and naming steps go
  through `dsa/opus.py`, which uses the Anthropic SDK and reads `ANTHROPIC_API_KEY` (as of 2d742ad).
- `coach/from_dsa.py` approximates the pro z-score as the mean and SD across the pros' per-player medians. That's
  my reading of the output format, not the article's exact method, and it has only been tested on synthetic files.
- Off Policy offers to run the analysis for you. Their email is in the article.
- Licenses: upstream code is MIT; the models it downloads keep their own licenses.
