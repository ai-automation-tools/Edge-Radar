# Edge-Radar Roadmap

*Last updated: 2026-10-03.* This file lists open work only. Shipped items, review findings,
performance history and the reasoning behind each item are in [CHANGELOG.md](./CHANGELOG.md).
The pre-cleanup roadmap is archived verbatim at the end of that file, and every item ID below
resolves there.

Work in this order: **execution correctness, then measurement, then risk controls, then data
quality, then UX, then features.** Hold all sizing (`KELLY_FRACTION` <= 0.5, `UNIT_SIZE=1.00`)
until S15 says otherwise.

---

## 1. Money-path defects: fix next

| ID | Item | Effort |
|----|------|--------|
| **B2** | **Unmapped sports fall back to a 12.0 stdev** (`edge_detector.py:861, 1028`). This is latent while those sports only trade moneylines. Fail closed (`None`, no edge) and add the soccer-league and WNCAAB entries. | S |
| **M2** | **Tennis markets are fetched but never scored outside Wimbledon.** `KALSHI_TO_ODDS_SPORT` maps `KXATPMATCH`/`KXWTAMATCH` only to `tennis_*_wimbledon`. Map tour-level Odds API keys per tournament, or drop tennis from the default scan deliberately. Surfaced by Integration-Drift-Check's "no fresh odds feed" line. | S |
| **M3** | **Kalshi's web dialog now defaults new API keys to Ed25519**; `kalshi_client.py` signs RSA only. Document "choose RSA" in `docs/setup`, or add Ed25519 signing before the next key rotation. | S |
| **B6(a-c)** | (a) The weather adjustment is applied after the side is chosen. (b) `CATEGORY_MAP` prefix shadowing sends a future `KXEPLSPREAD` to `game`. (c) Lower the log level of the "0 candidate events" warnings to DEBUG, and check why June markets still get scanned. | S |

## 2. Measurement: CLV and strategy state (Priority 0a, phases 2-4)

S8 (CLV capture) shipped 2026-09-10 and S9 (the CLV section of `betting_analysis.py`) on 2026-09-29. Everything below reads from them.

| ID | Item | Effort |
|----|------|--------|
| **S10** | **`strategy_state.json`, protective only.** Per segment it records `last_settled_at`, `evidence_status`, `expires_after_days` and a default of dry-run when stale. It can demote a segment to dry-run, raise a floor or cap a stake, and nothing else. **Once it ships, remove the `.env` pilot floors** (`MIN_EDGE_THRESHOLD_NFL`, `_NCAAF`, `_MLB_SPREAD`). | M |
| **S6** | **`risk_config_fingerprint()`**: hash the inputs the executor actually runs with (`.env`, `.bat` overrides, post-import module globals, strategy-state and eligibility-cache versions). Print it from `doctor.py` and the daily summary. This also closes S23 (balances quoted in docs going stale): `doctor.py` becomes the only place a balance is stated. | S |
| **S11** | **Shadow diagnostics, log only:** `calibrated_edge` at lambda 0.16/0.25/0.40, `gate3_ceiling_would_reject` at 0.20/0.30, and a `legacy_gateset` label. Review firing rates after one full cycle. | S |
| **S12** | **Six-line daily scoreboard:** eligibility, fingerprint, open exposure, 30d CLV with CI and coverage, segments in dry-run, and distance to each kill switch. | S |
| **S16** | **Kill switches:** global negative CLV sends everything to dry-run, segment negative CLV sends that segment to dry-run, and fewer than 150 captures in 120 days sends everything to dry-run. Distances are computed mechanically for S12. | S |
| **S13** | **Re-run `calibration_study.py` and `correlation_check.py` against CLV** once enough captures exist. Lambda's CI is currently [-0.04, +0.42]. | S |
| **S14** | **Maker-fill A/B.** Every fill today is a taker fill, and fees cost 3.14pt of ROI. Assign by deterministic ticker hash, 25% maker / 75% taker, with sizing unchanged. Recompute edge at the limit price, and log scan, limit and fill prices plus fee role. | M |
| **S15** | **Day-90 checkpoint, around 2026-12-09.** If coverage is below 60%, fix capture first. If the CI straddles zero, shrink the book or stop. If the lower bound is above 0 with 150 or more captures, raise `UNIT_SIZE` to $1.50, and only that. | S |

## 3. Model and gate follow-ups

| ID | Item | Effort |
|----|------|--------|
| **B5** | **Futures N-way devig is proportional**, which inflates longshot fair values. Switch to power or Shin devig, and skip incomplete books (raw implied total < 1.05). Affects Kalshi futures (`futures_edge.py`). | M |
| **T4** | **Newly covered market types flood the book before they can be calibrated.** Options: a higher floor until first calibration, a per-shape batch cap, or a per-(sport, category) share cap. | S-M |
| **GT1** | **Three unaligned NO-side knobs** (Gate 4.6, 4.6b and F4 damping). Check whether one edge-vs-price surface can reproduce all three before merging any of them. | M |
| **MLB** | Re-check MLB totals after about 20 more settles under Gate 3.55. Align the totals `n_books` floor (3) with moneyline (5). Once rows carry `n_books`, re-run `book_width_check.py` in direct mode. | S |
| **B7** | **Sharp books never arrive** (`regions=us`, and Pinnacle/Circa are `eu`). **Blocked on an operator quota decision:** add keys, apply `eu` only to the pre-execution scan, or lengthen the cache TTL. Prune `BOOK_WEIGHTS` either way. | S |
| **R23b** | On a 429, back off and retry the same key. Only mark a key exhausted on a 401. | S |
| **C9** | Soccer total stdev is 1.5, but realized data shows 1.86. Change it only with a backtest, because soccer totals are currently profitable. | S |
| **C4b** | Cap the edge for the `high` confidence label. Measure first, since High underperforms even at low edge. | S |

## 4. Scheduled checks and watch items

| ID | When | Check |
|----|------|-------|
| **NCAA-BB** | ~Nov 2026 | Run a live scan to confirm `KXNCAAMB*`/`KXNCAAWB*` markets resolve end to end. No code change expected. |
| **R7-exp** | ~30 more settles | Is the live `MIN_MARKET_PRICE=0.10` longshot lane worth keeping? Judge it on CLV, not ROI. |
| **GT3** | Once the gate has rejected real candidates | Is `MAX_MARKET_PRICE=0.75` actually binding? It shipped without evidence. |
| **S26b** | One quota cycle | Keep the daily `x-requests-used` readings per key to learn the Odds API reset model. Check key `...44681c` (401, likely a typo in `ODDS_API_KEYS`). |
| **S24** | Next occurrence | MLS LAG-NE 09-05 produced no edge because `find_market_event` found 0 candidates, likely a team-name mapping miss. |

## 5. Hygiene and tooling

| ID | Item | Effort |
|----|------|--------|
| **S22** | Report ROI as `net_pnl / (cost + fees)`. A total loss currently prints -107%. | XS |
| **T3** | CI: pytest on PR, import smoke, lint, detect-secrets. Only `deploy.yml` and Dependabot exist. | S |
| **T1/T2** | Mocked integration tests (scan→risk→execute, settle→report→CLV) plus deterministic API fixtures. | M |
| **R24c** | Make `install_windows_task.py status` reflect every live task under `\AI-Projects\Edge-Radar-MikesAILab\`. | S |
| **GT2** | Add one reference table of the 8 sizing-cap steps near `size_order`. | XS |
| **H7** | Move `BOOK_WEIGHTS` into config. Pairs with B7. | S |
| **H8** | Write a runbook for rotating the Kalshi RSA key. | XS |
| **H2 / H3** | Split `requirements.txt` into core, dev and research. Separate runtime state from the source tree. | S |
| **Q6** | Package `scripts/` and retire the `sys.path` hacks. | L |
| **R19** | Complete `FUTURES_ALIASES` for NBA/NHL/MLB. See the archive for the rest of the scope. | M |

## 6. Dormant until prediction markets are re-enabled

`ALLOW_PREDICTION_BETS=false` (Gate 4.7) blocks all of these today. If it is ever flipped, **C10c must land first.**

| ID | Item | Effort |
|----|------|--------|
| **R25b** | Add TTLs to the prediction-module caches (crypto 1h, weather 6h, spx 5min, mentions/companies 24h). | M |
| **R25c** | Rebuild the crypto model with tests, then port the same pattern to the others. | L |
| **C10c** | Replace `edge * 20` with `min(edge / 0.01, 10)` in all 7 prediction scanners, as part of R25c. | S |
| **M1-M4** | Crypto ensemble, SPX vol model, weather calibration, mentions seasonality. Gated on R25b and R25c. | L |

## Backlog (no committed date)

- **Sports data:** bullpen availability, injury impact scoring, wind direction vs stadium, umpire tendencies, platoon splits.
- **UX:** interactive pick mode (U3), and a single `scan.py session` command (U4).
- **Service/web track (A2-A9):** service layer, then DB, then FastAPI plus idempotent execution, then job runner, locks and secrets, then a UI. No web surface exists today.
