# Pre-submission rules audit (issue #31)

Source of the 18 rules: `BUILD_SPEC.md` §4 (authoritative copy: the hackathon rules page).
Audited 2026-10-18 against the near-final repo. Status: `pass`, or `needs owner` where only the
repo owner can act (nothing is silently left open).

| Rule | Requirement (short) | Evidence | Status | Action |
|---|---|---|---|---|
| 1 | Solo or team of ≤4; one team per participant | Team roster is declared on the WeMakeDevs submission form (not in the repo) | pass | confirm the roster at submission |
| 2 | FalkorDB is the primary graph DB and central to the product | README "Architecture" + "Graph data model"; `lib/graph.py`; every feature reads/writes FalkorDB | pass | — |
| 3 | Graph does real work; product dead without FalkorDB | 7a path enumeration (`lib/queries.py`), 7b score and **7c choke-point counts in Cypher** (`lib/chokepoints.py` — `UNWIND`/`count` over 7a paths, moved from Python during this audit), memory diff (`lib/memory.py`), `algo.betweenness` cross-check. Python only projects rows and formats. `lib/queries.py::score_path` is a pure formula used for ranking display | pass | — |
| 4 | Any run method for FalkorDB | FalkorDB Cloud (dev + live deploy) and local Docker (`docker-compose.yml`); verified both (#30, HANDOFF) | pass | — |
| 5 | Name every track entered | README "Track(s)": Track 01 and Track 02 (memory layer shipped, #23). Name both on the form | pass | name Track 01 + Track 02 at submission |
| 6 | Only public/synthetic/own data | `data/findings.json` is synthetic (`data/gen_findings.py`, deterministic); `data/findings.captured.json` comes from our own app on loopback; `data/demo_target.py` refuses non-loopback hosts and `data/capture_findings.py` refuses non-loopback URLs and never follows redirects (`tests/test_capture.py`) | pass | — |
| 7 | Event window Oct 15 00:01 – Oct 18 23:59 IST | All 44 commits are dated 2026-10-18 IST (first at 00:43) — inside the window | pass | submit before 23:59 IST |
| 8 | Main coding begins after the event starts | First commit 2026-10-18 00:43 IST; no earlier history | pass | — |
| 9 | Original work during the event is what's judged; libraries allowed | `docs/REUSE.md` lists the only lifted items (taxonomy files, findings-schema shape); loopback target and capture script written fresh | pass | — |
| 10 | Public repo; README with setup + graph model + the Cypher/algorithms; demo video; live deployment (or local setup); track | Repo public (verified via API). README has setup (A/B/C), model, verbatim queries, architecture, tracks. Local path verified from a fresh clone (#30). **Pending:** live URL (`render.yaml`, `docs/deploy.md` ready, needs the Render account/env vars) and demo video link | needs owner | deploy on Render, record/upload video, fill both links in README |
| 11 | Disclose AI-assistant use | README "Disclosure" paragraph (BUILD_SPEC §5 text, "Built with Claude Code") present and unchanged | pass | — |
| 12 | Participants understand and can explain the code | `docs/graph-model.md`, README query walk-through, `docs/HANDOFF.md` decisions (e.g. native memory vs Graphiti, #20 rename), `docs/sample-run.md` once recorded; code is commented per module | pass | rehearse the live explanation (model, 7a/7b/7c, architecture) |
| 13 | Not entirely AI-generated; meaningful contribution/verification | Verification evidence: live Cloud + fresh-clone Docker runs, 29 tests, deletion proof of the choke point, bug found and fixed in a clean install (pydantic pin) | pass | keep the walkthrough personal in the video |
| 14 | Prize/side-prize info | Informational. Blog post for the side prize: `docs/blog.md` | pass | submit the blog per the form |
| 15 | IP belongs to the team; agree ownership internally | Not a repo matter; LICENSE is MIT, "CrownPath team" | needs owner | confirm ownership among the team before submitting |
| 16 | Respect everyone | No conduct issues | pass | — |
| 17 | No harassment/plagiarism/judging manipulation | Reuse disclosed in `docs/REUSE.md`; no manipulation | pass | — |
| 18 | Follow rules and the Code of Conduct | See rows above | pass | — |

## Cross-checks requested by #31

- **Rules 2/3 — no path logic in Python:** #15 (7a) runs the path match in Cypher; #16 (7b) formula
  is also evaluated in Cypher via `reduce`; #21 (7c) now counts in Cypher. Fixed during this audit.
- **Rule 6 — loopback guard real:** tests `test_target_refuses_non_loopback_hosts`,
  `test_capture_refuses_non_loopback_url`, `test_capture_cli_refuses_remote_target`.
- **Rule 10 — README content:** queries pasted from `lib/queries.py` / `lib/chokepoints.py` /
  `lib/memory.py`; both run paths documented.
- **Rule 11:** disclosure paragraph verified present after the README rewrite.
- **Rule 12:** modules carry docstrings explaining intent and limits (e.g. the Cypher `LIMIT` caveat).
- **Credentials:** `.env` is untracked and `.gitignore`d; the FalkorDB password and host were searched
  for across all history (`git log --all -p`) — 0 hits.
- **Commit window:** 44/44 commits on 2026-10-18 IST.
- **Claude attribution:** none in any commit, PR, issue or comment added by this team's later work
  (checked: zero trailers in every commit after `674f717`); the only Claude text is the intended
  Rule-11 "Built with Claude Code" README disclosure. Four early planning-session commits
  (`3b4365b`, `dc17d90`, `fc1ba1d`, `b3263a9`) carry `Co-Authored-By: Claude ...` trailers; by the
  owner's decision this old history is kept as is (not rewritten). GitHub's contributors API lists
  only humans.
