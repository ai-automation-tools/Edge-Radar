<div align="center">

# ⏰ Edge-Radar Scheduled Tasks

**The repo owner's live Windows Task Scheduler setup — a full scan → execute → email → settle → reconcile → calibrate → review pipeline that runs unattended.**

[![Scheduler](https://img.shields.io/badge/Windows-Task%20Scheduler-0078D4?style=for-the-badge&logo=windows&logoColor=white)](#registering-the-tasks)
[![Pipeline](https://img.shields.io/badge/Pipeline-~20%20Tasks-8B5CF6?style=for-the-badge)](#at-a-glance--all-tasks)
[![Times](https://img.shields.io/badge/Times-PST%20%C2%B7%20ET%20noted-2ea44f?style=for-the-badge)](#daily-fire-sequence)
[![Templates](https://img.shields.io/badge/Templates-Copy%20%26%20Adapt-F97316?style=for-the-badge)](#reproducing-this-on-your-own-machine)

</div>

> [!NOTE]
> **This is the actual schedule the repo owner runs — published as a reference and recommended starting point, not a turnkey installer.** Build something similar, tuned to your own slate, time zone, and risk appetite. The owner's literal `.bat`/`.sh` files are gitignored (they hardcode a machine path and a private inbox), so this doc carries **sanitized templates** to copy — see [Reproducing this on your own machine](#reproducing-this-on-your-own-machine). Placeholders: `<YOUR_SENDER>` is the verified-domain address reports send **from** (`.env` → `RESEND_FROM`); swap the destination `mikeschecht@gmail.com` for your own (`.env` → `NOTIFY_EMAIL`). Want just the minimal "execute + settle + calibration" core? Start with [`AUTOMATION_GUIDE.md`](../setup/AUTOMATION_GUIDE.md) and its one-command installer.

**Location:** `\Edge-Radar\` Task Scheduler folder &nbsp;·&nbsp; **Times:** PST (ET in parentheses) &nbsp;·&nbsp; the only active scheduling mechanism — legacy Claude Desktop email routines were consolidated here 2026-04-22, and any `SKILL.md` left under `~/.claude/scheduled-tasks/` is a stale artifact, not a live trigger.

<details>
<summary><b>Changelog</b></summary>

- **2026-09-23** — **report emails no longer spawn a Claude session, and each `Email-*` task was folded into its scan task.** The 8 `Run-Reports/*.sh` scripts (each a `claude --dangerously-skip-permissions -p` run) are retired to `scripts/custom/Shell-Scripts/Run-Reports/_retired-2026-09-23/`, replaced by the tracked `scripts/schedulers/automation/render_report_email.py <preset>`: it renders the report markdown to inline-styled HTML (markdown-it-py) and sends through the unchanged `send_report_email.py` (Resend). No model involved, tables byte-exact, subjects and tags unchanged. Then **13 scan→email pairs became 13 tasks with two actions each** (scan, then email) — Task Scheduler runs action 2 even when action 1 exits non-zero (verified with a probe task), so the email fires the moment its scan finishes instead of 10–20 min later on a separate clock that could drift across DST. Unregistered: the 9 `Email-*` tasks in `\Edge-Radar-MikesAILab\` (incl. `Email-Longshot`, whose action is still `maintenance/email_longshot_scan.bat`) plus 4 in `\AI-Projects\Edge-Radar-AltAgents\` for the Edge-Radar-Agy fork (Day/Evening/Late/Settle). Time limits unchanged; pre-change XML in `.claude/temp/task-backup-2026-09-23/`. Verified: `Daily-Summary` run via Task Scheduler → `LastTaskResult=0`, email sent. Net: ~41 fewer Claude sessions a week, 13 fewer tasks, and `--dangerously-skip-permissions` gone from every unattended email job. The Weekly-Analysis email lost its model-written summary bullets — it is now just the rendered report. Consolidation audit 2026-09-23 #6 and #7.
- **2026-09-11** — **every daily-or-more-frequent task now launches through `scripts/schedulers/run-hidden.vbs`**, so no console window flashes on the desktop. Task Scheduler runs a `.bat`/`.sh`/`python.exe` action through a visible `cmd.exe` under an interactive token; `CLV-Capture` at every 5 minutes made that 288 interruptions a day. The wrapper is `wscript.exe "run-hidden.vbs" "<original exe>" <original args>` — it `Run()`s the original command with window style 0 and `WScript.Quit(rc)`, **so the exit code still reaches the scheduler** and a real failure is still a real failure. Applied to 15 tasks (the three `All-Sports-*` executions, `Daily-Polymarket-Execution`, `Daily-Summary`, all six `Email-*` dailies, `Longshot`, `Reconcile`, `Hourly-Settle`, `NightlySettle`); **weekly and one-shot tasks were deliberately left visible** — one flash a week is not worth the indirection. Verified on `Hourly-Settle` and `Daily-Summary`: `LastTaskResult=0`, report regenerated, `kalshi_settlements.json`/`kalshi_trades.json` written. Triggers, principals and settings unchanged (`Set-ScheduledTask -Action` only); pre-change XML for all 15 is in `.claude/temp/task-backup-2026-09-11/`. `pythonw.exe` was tried first for the two settle tasks and **rejected**: it gives the process no console, so `sys.stdout` is `None` — bare `print()` silently no-ops, but any `sys.stdout.write`/`flush` or logging `StreamHandler` anywhere in the settler's import graph would raise. The wrapper keeps a real (hidden) console, so nothing in that graph has to be audited. The `.vbs` lives under the gitignored `scripts/schedulers/`, so this appears in no diff.
- **2026-08-26** — added **`NFL-Week1-Review`** (one-shot 2026-09-15 7:00 AM). NFL live entries were frozen the same day (S1: 26 open positions, 31% of bankroll, zero settled history), and the 26 held positions settle across Week 1 — so this task is the dated, pre-declared exit from that freeze. **It is the first scheduled task permitted to change a risk threshold**, which is why the decision lives in `scripts/backtest/nfl_week1_review.py` (branch rule written 08-26, while nothing was at stake) rather than in the model's judgement: the prompt explicitly forbids second-guessing it, re-running it for a different answer, or editing `.env` directly. Fails closed — too few settlements, market prices better, model over-claiming, or any exception leaves NFL frozen. Branch A caps the unfreeze at an 0.08 floor (~2.7x global), the only per-sport volume limit expressible until S4 ships. Verified today on the live path: `--apply` with 0 NFL settlements reported branch C and left `.env` byte-identical. **Rehearsed live the same day** (`schtasks` manual run, 2m15s, `LastTaskResult=0`): settled -> gate -> report -> email -> temp-file cleanup, all five steps. It correctly refused to act (branch C) and changed nothing — `.env` still `1.0`, no docs touched. The one-shot 09-15 trigger survived the manual run (`NextRunTime` unchanged). Two things the rehearsal surfaced: today's n=0 is because Week 1 has not been *played* (every NFL ticker is a 26SEP09-26SEP14 game), not MNF settlement lag as the runbook assumed; and the trade log holds 22 `error`-status rows, 6 of them NFL, which may mean the at-risk total and the eventual settled count are both off — worth a `kalshi_settler.py reconcile` before 09-15.
- **2026-07-31** — **`Calibration` window widened `--days 7` → `--days 30`; the C8 stdev loop had never actually calibrated anything.** `save_calibration_stdevs()` is handed the **day-filtered** settled list and needs `_MIN_CALIB_SAMPLES=20` rows per (sport, category) before it will move a value. Only ~22 bets settle in any 7-day window across *all* sports and categories, so every pair was skipped every week and the hardcoded defaults were written straight back — `data/cache/calibration_stdevs.json` has been byte-identical to `edge_detector.SPORT_*_STDEV` for as long as it has existed. At `--days 30` MLB totals goes 17 → 28 settled and the loop fires: **`total_stdev.baseball_mlb` 3.45 → 4.005** on the first real run (gap +16.1%, n=28, se=0.085). That drops the phantom edge on MLB high-strike unders below the R28 8% NO floor, blocking 21 of 25 such bets. Full analysis: ROADMAP **T1**. The fix is in the gitignored `scripts/schedulers/maintenance/calibration.bat`, so it appears in no diff; `tests/test_calibration_config.py` now fails if the window is ever narrowed again. Cadence was **not** the problem — this task was already weekly. `MonthlyCalibration` (#15) — a duplicate that had never once run — was removed the same day.
- **2026-07-25** — **`Email-Polymarket-DryRun` renamed to `Email-Polymarket-Execution`.** The 07-23 entry below deferred this rename as cosmetic; it wasn't. The email announced itself as a "Daily Polymarket Dry-Run Report" while the paired task placed live orders, and its prompt never asked whether an order had been placed — so the one fact that matters most on an execute-enabled venue was the one the email didn't have to report. Re-registered preserving the daily 10:00 AM trigger/principal/settings; old task unregistered and `Polymarket-DryRun-Report.sh` deleted (superseded by `Polymarket-Execution-Report.sh`). Prompt now requires an **Execution Outcome** section led by whether an order filled. Log paths keep their `dryrun` filenames on purpose — append-only history from the dry-run window. `NextRunTime=2026-07-26 10:00 AM`.
- **2026-08-24** — **`Weekly-Futures-Execution` re-enabled** after the manual preview cycle it was waiting on since 2026-07-23. Preview run: 154 Kalshi futures markets, outrights fetched for 4 active sports (NFL/NBA/NHL/MLB), **0 opportunities above the 3% edge floor**. Task then fired via `schtasks /run` → `LastTaskResult=0`, report written, **0 orders** — the execute path is now exercised end-to-end. ⚠️ It places **real** orders from here (`DRY_RUN=false`); blast radius is `--max-bets 3 --min-bets 1 --budget 10% --unit-size 1` under `MAX_BET_SIZE=8`. Halt with `Disable-ScheduledTask -TaskPath "\Edge-Radar-MikesAILab\" -TaskName "Weekly-Futures-Execution"`. Also corrected a long-standing doc/code drift: every doc said `--budget 5%`, the `.bat` has always passed `--budget 10%%`. Docs (and the `.bat` header comment) now match the code — **sizing behavior unchanged**.
- **2026-07-23** — **`Daily-Polymarket-DryRun` now places real orders.** Added `--execute` plus batch caps (`--max-bets 2 --budget 10%`) after `POLYMARKET_DRY_RUN` was set to `false` in `.env`. The task keeps writing the evidence log either way (`--save` runs outside the execute branch). **Renamed to `Daily-Polymarket-Execution`** the same day (re-registered from exported XML, preserving trigger + principal; old task unregistered; re-validated `LastTaskResult=0`). The paired `Email-Polymarket-DryRun` job keeps its name for now — it only emails the report and is unaffected. Only futures are orderable; Gamma games are auto-excluded. Verified end-to-end same day: 4 opportunities risk-checked, **0 orders placed** (all rejected on `edge_below_threshold`, 1.1–2.6% vs the 3.0% floor), evidence log still written, exit 0.
- **2026-07-23** — **`Weekly-Futures-Execution` disabled.** C10 (futures composite recalibration) made Kalshi futures clear Gate 4 for the first time — the task had never been capable of placing a bet before, so its next Saturday run would have been the first-ever live futures order through an unexercised path. Disabled pending a manual futures cycle in preview. Re-enable with `Enable-ScheduledTask -TaskPath "\Edge-Radar-MikesAILab\" -TaskName "Weekly-Futures-Execution"`.
- **2026-07-21** — added `Email-Polymarket-DryRun` (daily 10:00 AM, 20-min buffer after the 9:40 scan) — pairs the Polymarket dry-run scan with an email like every other daily task. Emails the day's `reports/Polymarket/` report; on 0-opportunity days (no report written) it checks `logs/polymarket_dryrun_scan.log` and sends a short no-opportunities proof-of-life instead. Script: `Run-Reports/Polymarket-DryRun-Report.sh`, log: `logs/email_polymarket_dryrun.log`.
- **2026-09-23** — **`NightlySettle` retired** (unregistered). It ran the same `kalshi_settler.py settle` as `Hourly-Settle`, whose 10:35/11:35 PM passes already cover 11 PM ahead of `Reconcile`; it was slated to retire after a validation week in July and `Hourly-Settle` has run clean since. `install_windows_task.py install settle` now registers `Hourly-Settle` (hourly at :35) instead. Consolidation audit 2026-09-23 #8.
- **2026-07-20** — added `Hourly-Settle` (every hour at :35) — U1: hourly `kalshi_settler.py settle`, enabled by the M2 cross-process trade-log lock (concurrent settle+execute now merge-safe). Sharpens Gate 1 daily-loss accuracy intraday. `NightlySettle` kept as belt-and-suspenders during a validation week, then retire. Validated live (`LastTaskResult=0`).
- **2026-07-20** — added `Daily-Polymarket-DryRun` (daily 9:40 AM) — read-only Polymarket championship-futures scan appending to the PM2 edge-proving evidence log (`data/polymarket/dryrun_log.jsonl`). Places no orders; no paired email (output logs to `logs/polymarket_dryrun_scan.log`). Validated live (`LastTaskResult=0`).
- **2026-06-20** — added `Weekly-Futures-Execution` (Sat 9:00 AM, first futures automation) + paired `Email-Weekly-Futures` (Sat 9:20 AM); `futures_edge.py` now always writes a report on `--save` for 0-order-week proof-of-life. Both validated live (`LastTaskResult=0`, 0 bets, all gated).
- **2026-06-20** — per-task logging on every email shell script (`logs/email_*.log` with exit-code banners; see [Troubleshooting → Email task logs](#email-task-logs-added-2026-06-20)).
- **2026-05-31** — added `WeeklyAccountGraph` (Sun 9:00 AM) — publishes the account-growth graph to GitHub Pages via a `gh` push to master.
- **2026-05-17** — added daily 11 AM Midday-NoDateFilter + 2 PM Late-SameDay execute/email pairs; shifted `All-Sports-NextDay-Execution` 6:00 PM → 8:30 PM; retired the Mon/Thu 5:20 AM `All-Sports-NoDateFilter-Execution` + its email.

</details>

---

## At a Glance — All Tasks

### Active (Ready)

| # | Task | Schedule (PST) | What it does |
|:-:|:-----|:---------------|:-------------|
| 0a | `Daily-Summary` | Daily 4:50 AM | Generates morning P&L digest (yesterday settled + open exposure + today pending + 7-day context), **then emails it** (action 2) |
| ~~0b~~ | ~~`Email-Daily-Summary`~~ | — | **MERGED 2026-09-23 into #0a** as its second action |
| 1 | `All-Sports-SameDay-Execution` | Daily 5:05 AM | Scans NBA/NHL/MLB/NFL for **today's** games and places bets (`--date today`, budget 12%, max 7 bets), **then emails the report** |
| ~~2~~ | ~~`Email-SameDay`~~ | — | **MERGED 2026-09-23 into #1** |
| 3 | `All-Sports-NoDateFilter-Midday-Execution` | **Daily** 11:00 AM | Midday wide-net scan, no date filter (budget 8%, max 5 bets), **then emails the report**. Catches confirmed MLB starters, NBA/NHL morning-skate news, mid-morning sharp-money moves |
| ~~4~~ | ~~`Email-NoDateFilter-Midday`~~ | — | **MERGED 2026-09-23 into #3** |
| 5 | `All-Sports-SameDay-Late-Execution` | **Daily** 2:00 PM | Late same-day scan (budget 5%, max 4 bets, `--date today`), **then emails the report**. Catches late-breaking scratches, goalie confirmations, weather, sharp moves on tonight's games |
| ~~6~~ | ~~`Email-SameDay-Late`~~ | — | **MERGED 2026-09-23 into #5** |
| 7 | `All-Sports-NextDay-Execution` | **Sun-Thu** 8:30 PM | Scans for **tomorrow's** games (`--date tomorrow`, budget 12%, max 6 bets), **then emails the report**. Shifted from 6:00 PM 2026-05-17 — more next-day lines posted by 11:30 PM ET |
| ~~8~~ | ~~`Email-NextDay`~~ | — | **MERGED 2026-09-23 into #7** |
| ~~9~~ | ~~`NightlySettle`~~ | — | **REMOVED 2026-09-23.** Duplicate of #22 (`Hourly-Settle`), which runs the same command and covers the 11 PM slot at 10:35 and 11:35 PM |
| 10 | `Reconcile` | Daily 11:30 PM | Compares local trade log against Kalshi API positions, flags any drift |
| 11 | `Calibration` | **Sun** 7:00 PM | Weekly Brier-score refresh + calibration-curve report **+ the C8 stdev recalibration** (`model_calibration.py --days 30 --save`). **Window widened 7 → 30 on 2026-07-31** — at `--days 7` the C8 loop was a silent no-op (see the changelog note below). |
| 12 | `Backtest` | **Sun** 7:30 PM | Weekly equity curve, drawdown, Sharpe, strategy-comparison report |
| 13 | `Weekly-Analysis` | **Sun** 11:45 PM | End-of-week 7-day `betting_analysis.py` (headline, by sport/category/side/edge/confidence/price, calibration, longshots, streaks, daily P&L, full trade ledger), **then emails the report** |
| ~~14~~ | ~~`Email-Weekly-Analysis`~~ | — | **MERGED 2026-09-23 into #13** |
| ~~15~~ | ~~`MonthlyCalibration`~~ | — | **REMOVED 2026-07-31.** Redundant duplicate of #11 that had **never once run** (Last Run `11/30/1999`). #11 does the same job weekly. Unregistered with `schtasks /Delete`; the recreate command is in [section 15](#15-monthlycalibration--removed-2026-07-31). |
| 18 | `WeeklyAccountGraph` | **Sun** 9:00 AM | Refreshes the private Kalshi account-growth graph (live snapshot → HTML/PNG), written to a gitignored local folder only (`refresh_account_graph.py`) |
| 24 | `WeeklyOddsKeyProbe` | **Sun** 6:00 PM | Probes every Odds API key live (`check_odds_keys.py --live`) and refreshes `data/cache/odds_api_quota.json`. 14 requests/week against a 500/key/month allowance. **Added 2026-09-09** — a cached zero used to be believed forever, so a drained key was never contacted again and any reset went unobserved; 12 of 14 keys read 0 while 5154 requests were actually available. The root-cause fix is the `_ZERO_TTL_HOURS` expiry in `scripts/shared/odds_api.py`; this task catches a key going bad **before** a scan needs it. Runs the gitignored `scripts/schedulers/maintenance/odds_keys.bat`, so it appears in no diff. |
| 19 | `Weekly-Futures-Execution` ⚠️ **RE-ENABLED 2026-08-24** | **Sat** 9:00 AM | ⚠️ **PLACES REAL ORDERS.** Scans + executes championship/outright **futures** (NFL Super Bowl, NBA/NHL/MLB titles, NCAAB MOP, golf majors) via `scan.py futures --execute` (budget 10%, max 3, unit $1, `--exclude-open`). Offseason series with no Odds API outright data are skipped; golf only prices the 4 majors during their weeks, **then emails the report** (every week, 0-order weeks included). First futures automation (added 2026-06-20) |
| ~~20~~ | ~~`Email-Weekly-Futures`~~ | — | **MERGED 2026-09-23 into #19** |
| 21 | `Daily-Polymarket-Execution` | Daily 9:40 AM | ⚠️ **PLACES REAL ORDERS since 2026-07-23** (renamed from `Daily-Polymarket-DryRun` same day). Polymarket scan — championship futures **+ per-game ML/spread/total (PM1d)** — `scan.py polymarket --filter all --min-edge 0.01 --top 40 --max-bets 2 --budget 10% --save --execute`. Still appends the full funnel to `data/polymarket/dryrun_log.jsonl` + markdown to `reports/Polymarket/`. **Only futures are orderable** — Gamma-sourced games carry no US `market_slug` and are auto-excluded from execution. Full risk-gate chain applies; batch capped at 2 bets / 10% of bankroll. Halt this venue with `POLYMARKET_DRY_RUN=true`. **Then emails the report** led by the execution outcome, or a proof-of-life on 0-opportunity days |
| 22 | `Hourly-Settle` | **Every hour** at :35 | U1: runs `kalshi_settler.py settle` hourly (direct python, no .bat wrapper). Keeps the trade log fresh all day → Gate 1 daily-loss checks see intraday settlements. Safe alongside the execute tasks via the M2 cross-process lock. Replaced `NightlySettle`, retired 2026-09-23 |
| ~~23~~ | ~~`Email-Polymarket-Execution`~~ | — | **MERGED 2026-09-23 into #21** |
| 27 | `CLV-Capture` | **Every 5 min** | S8: samples the market book shortly before each open position's event starts and writes the whole closing book + CLV to the trade row. **Read-only at the venue** — calls `get_market()` only, never places/cancels/modifies an order. A pass with nothing due makes **zero API calls**, which is what makes the 5-minute cadence affordable; cadence buys capture coverage, and coverage is what makes a mean CLV trustworthy. Safe alongside the execute tasks: venue reads happen outside the M2 lock and captures are re-applied by `trade_id` against a fresh read inside it. Runs the gitignored `maintenance/clv_capture.bat`, log `logs/clv_capture.log`. **Added 2026-09-10** — CLV had returned nothing across 426 settlements because the settler derived it from a market that had already settled. |
| 28 | `Shadow-Book-NCAAF` | Daily 6:00 AM | **S21b: the exit ramp for the S21 NCAAF freeze.** **PLACES NO ORDERS AND RISKS NO MONEY** — `shadow_book.py settle` then `collect --filter ncaafb`. A freeze stops orders, so it also stops the settlements that would ever justify lifting it; NFL escaped that only because 19 positions were already in flight when S1 landed, while NCAAF was frozen holding nothing, pinning it at 11 settled forever against `nfl_week1_review`'s bar of 20. A Brier head-to-head needs only (model probability, market price, outcome) and **never needed a filled order**, so the model keeps scoring the sport and Kalshi settles the markets anyway. Taps **upstream of the risk gates** on purpose — `last_scan.json` is written post-gate and holds nothing at a 1.0 floor, while `scan_all_markets()` applies only the global min-edge. ~96 rows/scan. Read it with `shadow_book.py review --sport ncaaf --save`, which prints the S18 Brier pair plus a **margin-stdev sweep** — the direct read on S21's finding that the whole NCAAF edge was one uncalibrated parameter. Runs the gitignored `maintenance/shadow_book.bat`, log `logs/shadow_book.log`. **Added 2026-09-13.** |
| 25 | `Longshot-Scan` | Daily 8:00 AM | **Longshot profile** (P1), `--profile longshot`: championship futures + individual-game longshots, `--execute` under `DRY_RUN=true` on **Kalshi subaccount 1** (~$40). No real money -- the profile overlay sets `DRY_RUN=true`, and rows land in the shared trade log tagged `"profile": "longshot", "dry_run": true`. **`--profile longshot` is load-bearing**: without it the .bat runs the base `.env` (`DRY_RUN=false`, primary account) and every `--execute` places a real order. Moved here from the retired `Edge-Radar-Longshot` fork 2026-09-10; task path is still `\AI-Projects\Edge-Radar-Longshot\`. Runs the gitignored `maintenance/longshot_scan.bat`, log `logs/longshot_scan.log`. **Action 2 emails the scan** via `maintenance/email_longshot_scan.bat` to `mikeschecht+longshot@gmail.com` from a distinct sender name, so the profile's reports keep filtering separately now that both books come from one repo. Subject `Longshot \| Daily Dry-Run Scan` |
| ~~26~~ | ~~`Email-Longshot-Scan`~~ | — | **MERGED 2026-09-23 into #25** |
| 16 | `R8-Review` | **One-shot 2026-05-29 6:00 AM** | R8 cross-category dedup A/B review (~30 days post-ship). Slices ML/Total/Spread same-game cohorts and recommends per-sport `CROSS_CATEGORY_DEDUP_<SPORT>` flips |
| 17 | `U2-Review` | **One-shot 2026-05-14 7:00 AM** | U2 daily-summary digest 2-week post-ship review. Scans last 14 `daily_summary_*.md` files for firing-reliability + section coverage, spawns `claude -p` for code review pass, writes recommendations + operational checklist |
| 24 | `NFL-Week1-Review` | **One-shot 2026-09-15 7:00 AM** | ⚠️ **MAY EDIT `.env`.** S1b: the pre-declared exit from the S1 NFL freeze. Settles Week 1 first (MNF settles late), then runs `nfl_week1_review.py --apply`, which owns the decision and is the only thing allowed to touch `MIN_EDGE_THRESHOLD_NFL`. Branch A (model Brier <= market Brier over >=20 settled NFL bets, model not over-claiming) unfreezes NFL to a **capped 0.08 pilot floor** — never to normal sizing. Every other path, including any exception, leaves NFL frozen. Emails the verdict either way. Script: `maintenance/nfl_week1_review.sh`, log: `logs/nfl_week1_review.log`. Halt with `Disable-ScheduledTask -TaskPath "\Edge-Radar-MikesAILab\" -TaskName "NFL-Week1-Review"` |

### Disabled (kept for reference, not running)

| # | Task | Prior Schedule | Why disabled |
|:-:|:-----|:---------------|:-------------|
| 11 | `All-Sports-SameDay-Scan` | Daily 4:55 AM | Preview-only variant of task #1; execution variant is what runs |
| 12 | `All-Sports-NoDateFilter-Scan` | Daily 9:00 AM | Preview-only variant of task #2 |
| 13 | `MLB-NextDay-Scan` | 6:00 PM | Per-sport scan; replaced by consolidated `All-Sports-NextDay-Execution` |
| 14 | `NBA-NextDay-Scan` | 6:05 PM | Per-sport; replaced |
| 15 | `NHL-NextDay-Scan` | 6:10 PM | Per-sport; replaced |
| 16 | `NFL-NextDay-Scan` | 6:15 PM | Per-sport; replaced |

### Daily Fire Sequence

`[+email]` = the task's second action emails the report the moment the scan finishes (since 2026-09-23 — no separate email task, no buffer).

```
 4:50 AM  Daily    ─ Daily-Summary         [+email]  (yesterday P&L + exposure digest)
 5:05 AM  Daily    ─ All-Sports-SameDay-Execution [+email]
 9:00 AM  Sun      ─ WeeklyAccountGraph    (refresh + publish account graph to Pages)
 9:00 AM  Sat      ─ Weekly-Futures-Execution [+email] (futures scan + execute) [LIVE - re-enabled 2026-08-24]
 9:40 AM  Daily    ─ Daily-Polymarket-Execution [+email] (PM scan + EXECUTE -- places real orders)
11:00 AM  Daily    ─ All-Sports-NoDateFilter-Midday-Execution [+email]
 2:00 PM  Daily    ─ All-Sports-SameDay-Late-Execution [+email]
 8:30 PM  Sun-Thu  ─ All-Sports-NextDay-Execution [+email]
 6:00 PM  Sun      ─ WeeklyOddsKeyProbe   (live Odds API quota refresh)
 7:00 PM  Sun      ─ Calibration
 7:30 PM  Sun      ─ Backtest
11:30 PM  Daily    ─ Reconcile
11:45 PM  Sun      ─ Weekly-Analysis       [+email] (end-of-week 7-day report)

  :35 every hour   ─ Hourly-Settle          (settle sweep; :35 slot is clear of all task minutes)
```

### Fires-Per-Day Totals

Emails are no longer separate fires — each rides its scan task.

| Day | Morning | Midday | Afternoon | Evening | Nightly | Day total |
|:----|:-------:|:------:|:---------:|:-------:|:-------:|:---------:|
| Mon-Thu | 2 (same-day + Polymarket @ 9:40) | 1 (Midday-NoDateFilter) | 1 (Late-SameDay) | 1 (NextDay) | 1 | **6** |
| Fri | 2 (same-day + Polymarket) | 1 | 1 | 0 | 1 | **5** |
| Sat | 3 (same-day + Futures-Execution @ 9:00 + Polymarket @ 9:40) | 1 | 1 | 0 | 1 | **6** |
| Sun | 2 (same-day + Polymarket) + WeeklyAccountGraph @ 9:00 | 1 | 1 | 3 (NextDay + Calibration + Backtest) | 2 (Reconcile + Weekly-Analysis) | **10** |

**Monthly add-on:** none. `MonthlyCalibration` was removed 2026-07-31 — the weekly Sunday `Calibration` (#11) covers it.

**Hourly add-on (2026-07-20):** `Hourly-Settle` fires 24×/day at :35 — excluded from the per-day totals above to keep them readable.

---

## Reproducing this on your own machine

The roster above is what the owner runs. To stand up the equivalent, you recreate two kinds of files from the sanitized templates below, then register each with `schtasks`. You do **not** need all 20 tasks — see the [minimal core](#minimal-viable-automation) note.

### Placeholders

Substitute these everywhere they appear:

| Placeholder | Meaning | Example |
|:--|:--|:--|
| `<REPO_ROOT>` | Absolute path to your Edge-Radar checkout | `C:\Users\you\Edge-Radar` |
| `<YOUR_EMAIL>` | Inbox you want reports delivered **to** | `you@example.com` |
| `<YOUR_SENDER>` | Verified-domain address reports are sent **from** | `Edge-Radar <fleet@send.yourdomain.com>` |
| `<GIT_BASH>` | Path to `bash.exe` from Git for Windows | `C:\Program Files\Git\bin\bash.exe` |

`<YOUR_EMAIL>` and `<YOUR_SENDER>` have homes in `.env` (`NOTIFY_EMAIL`, `RESEND_FROM`) — see [`../../.env.example`](../../.env.example). The email templates read them from there. The **API key does not**: `RESEND_API_KEY` lives in the OS environment (Windows: `setx RESEND_API_KEY "re_..."`), so Task Scheduler — which builds a fresh environment at every launch — picks up a rotated key on the next run with no file edit and no reboot. A User-scoped variable is invisible to `SYSTEM`, which is why these tasks run as your own user, not `SYSTEM`.

> **Time zone:** all schedule times in this doc are the owner's local PST, with ET in parentheses. Task Scheduler fires on **your** machine's local time — pick times that make sense where you are, not these literal values.

### Template A — execute/scan wrapper (`.bat`)

A self-locating wrapper avoids hardcoding your path: `%~dp0` is the directory the `.bat` lives in, so `cd /d "%~dp0..\..\.."` walks up to the repo root (adjust the number of `..` to match where you save it). Save as e.g. `same_day_execute.bat`:

```batch
@echo off
REM ── Same-Day Execute — all sports, today's games ──────────────────────────
REM  WARNING: places live orders when DRY_RUN=false in .env. Verify first.

REM Self-locate the repo root (adjust ..\..\.. to your folder depth):
cd /d "%~dp0..\..\.."

echo --- Portfolio Status (Before) ---
.venv\Scripts\python.exe scripts\kalshi\kalshi_executor.py status

echo --- Scanning and Executing ---
.venv\Scripts\python.exe scripts\scan.py sports ^
  --unit-size 1 --max-bets 7 --min-bets 3 --budget 12%% ^
  --date today --exclude-open --save ^
  --report-dir "reports\Sports\schedulers\same-day-executions" --execute

echo --- Portfolio Status (After) ---
.venv\Scripts\python.exe scripts\kalshi\kalshi_executor.py status
```

> If you'd rather not rely on `%~dp0`, replace the `cd /d` line with the absolute `cd /d <REPO_ROOT>`. The `%%` on `12%%` is required — a literal `%` must be doubled inside a `.bat`.

The other execute variants are the same wrapper with different flags + `--report-dir`:

| Variant | Flags that differ |
|:--|:--|
| Same-day (morning) | `--max-bets 7 --budget 12% --date today` |
| Midday wide-net | `--max-bets 5 --budget 8%` *(no `--date` — scans all dates)* |
| Late same-day | `--max-bets 4 --budget 5% --date today` |
| Next-day | `--max-bets 6 --budget 12% --date tomorrow` |

### Template B — maintenance wrapper (`.bat`)

Settle, reconcile, calibration, backtest, weekly-analysis, and daily-summary are all the same one-line pattern — just a different Python entry point:

```batch
@echo off
cd /d "%~dp0..\..\.."
.venv\Scripts\python.exe scripts\kalshi\kalshi_settler.py settle
```

Swap the last line for the job you're wrapping:

| Task | Last line |
|:--|:--|
| Settle | `… scripts\kalshi\kalshi_settler.py settle` |
| Reconcile | `… scripts\kalshi\kalshi_settler.py reconcile` |
| Calibration (weekly) | `… scripts\kalshi\model_calibration.py --days 7 --save` |
| Backtest | `… scripts\backtest\backtester.py --simulate --save` |
| Weekly-Analysis | `… scripts\kalshi\betting_analysis.py --days 7 --save` |
| Daily-Summary | `… scripts\kalshi\daily_summary.py --save` |

### Template C — report emailer (`render_report_email.py`)

No template to copy: the emailer is a tracked script, `scripts/schedulers/automation/render_report_email.py <preset>`. It renders the report markdown to inline-styled HTML (markdown-it-py, so the tables are byte-exact) and sends it through `scripts/custom/Python/send_report_email.py`. No model is involved. Presets, each with its report folder, subject, tag and `logs/email_*.log` baked in:

| Preset | Pairs with | Subject |
|:--|:--|:--|
| `daily-summary` | `Daily-Summary` | `Edge-Radar \| Daily Summary` |
| `same-day` | `All-Sports-SameDay-Execution` | `Edge-Radar \| Same Day Execution Report` |
| `nodatefilter-midday` | `All-Sports-NoDateFilter-Midday-Execution` | `Edge-Radar \| NoDateFilter Midday Execution Report` |
| `same-day-late` | `All-Sports-SameDay-Late-Execution` | `Edge-Radar \| Same-Day Late Execution Report` |
| `next-day` | `All-Sports-NextDay-Execution` | `Edge-Radar \| Next Day Edge Report` |
| `polymarket` | `Daily-Polymarket-Execution` | `Edge-Radar \| Daily Polymarket Execution Report` |
| `weekly-futures` | `Weekly-Futures-Execution` | `Edge-Radar \| Weekly Futures Execution Report` |
| `weekly-analysis` | `Weekly-Analysis` | `Edge-Radar \| Weekly Performance Analysis` |

- **Which report:** the newest file in the preset's folder modified within the last 3 hours (`--max-age-hours`), **not** the one named with today's date. Report filenames carry the UTC date, so the PT evening runs (NextDay 8:30 PM, Weekly-Analysis 11:45 PM) write tomorrow's name.
- **No report:** exits 2 and sends nothing, so a failed scan never produces a stale email. The exception is `polymarket`, where no report is the normal zero-opportunity case: it sends a proof-of-life instead. The Polymarket email always leads with an **Execution outcome** section — the last run of `logs/polymarket_dryrun_scan.log`, minus INFO lines.
- **Log:** one result line per run, appended to the same `logs/email_*.log` file the retired `.sh` scripts used.
- **Preview without sending:** `python scripts/schedulers/automation/render_report_email.py same-day --dry-run out.html`.

`send_report_email.py` is a thin wrapper over the Resend REST API (one `POST`, no SDK). It exists so the provider lives in **one** file, and so every successful send stamps `logs/last_email_sent.json` — a file that goes stale is something you can alert on when the mail itself is what's broken. Probe it without spending quota: `python scripts/custom/Python/send_report_email.py --check`.

> **History.** Until 2026-09-23 each email was a `Run-Reports/*.sh` script that spawned `claude --dangerously-skip-permissions -p` to read the report and build the HTML (retired to `scripts/custom/Shell-Scripts/Run-Reports/_retired-2026-09-23/`). Before that, the prompts ended with *"use the agentmail skill to send"* and the inner Claude authored its own API call each night, producing 40+ near-duplicate `send_*_email_<date>.py` files. Rendering deterministically removed the model from the path entirely.

### Registering the tasks

All tasks live in a `\Edge-Radar\` Task Scheduler folder. Two `schtasks` shapes cover everything.

**A `.bat`-backed task (scan/execute/maintenance):**

```powershell
schtasks /Create /TN "\Edge-Radar\All-Sports-SameDay-Execution" `
  /TR "<REPO_ROOT>\scripts\schedulers\same_day_executions\same_day_execute.bat" `
  /SC DAILY /ST 05:05 /F
```

**Adding the email as a second action** (`schtasks` can only create one action, so append it with PowerShell). Task Scheduler runs actions in order and runs action 2 even if action 1 exits non-zero, so the email fires as soon as the scan finishes:

```powershell
$t     = Get-ScheduledTask -TaskPath "\Edge-Radar\" -TaskName "All-Sports-SameDay-Execution"
$scan  = $t.Actions[0]
$email = New-ScheduledTaskAction -Execute "wscript.exe" `
  -Argument '"<REPO_ROOT>\scripts\schedulers\run-hidden.vbs" "<REPO_ROOT>\.venv\Scripts\python.exe" "<REPO_ROOT>\scripts\schedulers\automation\render_report_email.py" same-day'
Set-ScheduledTask -TaskPath "\Edge-Radar\" -TaskName "All-Sports-SameDay-Execution" -Action $scan,$email
```

Swap `same-day` for the preset matching the scan (see [Template C](#template-c--report-emailer-render_report_emailpy)). `run-hidden.vbs` only suppresses the console flash; `"<REPO_ROOT>\.venv\Scripts\python.exe" "…\render_report_email.py" same-day` as a plain action works the same.

> [!IMPORTANT]
> **`schtasks /Create` cannot set `StartWhenAvailable`, and every task needs it.**
> Without it, a trigger whose time passes while the machine is off or asleep is
> **dropped and never retried** — and it is silent: the task still reads `Ready`,
> and `LastTaskResult` stays `267011` ("has not yet run"), which is identical to
> a task legitimately waiting for a date that has not arrived. **Nothing
> distinguishes "waiting" from "missed forever."**
>
> Two dated one-shot reviews here were lost exactly this way and went unnoticed
> for ~4 months (`U2-Review` 2026-05-14, `R8-Review` 2026-05-29). One-shot tasks
> are where it is fatal; for a weekly it costs a full cycle, which for
> `Calibration` can push the stdev cache past `CALIBRATION_STDEVS_TTL_DAYS`.
>
> Set it after every create:
>
> ```powershell
> $t = Get-ScheduledTask -TaskName "All-Sports-SameDay-Execution" -TaskPath "\Edge-Radar\"
> $t.Settings.StartWhenAvailable = $true
> Set-ScheduledTask -TaskName "All-Sports-SameDay-Execution" -TaskPath "\Edge-Radar\" -Settings $t.Settings
> ```
>
> `install_windows_task.py` now does this itself after each `/Create`, and warns
> if it cannot.
>
> **On execution tasks this is a real behaviour change**, not just reliability: a
> missed run fires when the machine wakes, against whatever slate is live *then*
> rather than the one intended for its scheduled time. Bounded by Gate 4.8
> (`ALLOW_LIVE_BETS=false`), Gate 3.7, and each task's own `--budget` /
> `--max-bets`. Enabled on the owner's six execution tasks 2026-09-10 by
> operator decision.

**Schedule shapes you'll need:**

| Cadence | `schtasks` flags |
|:--|:--|
| Every day | `/SC DAILY /ST HH:MM` |
| Sun–Thu only | `/SC WEEKLY /D SUN,MON,TUE,WED,THU /ST HH:MM` |
| Sundays | `/SC WEEKLY /D SUN /ST HH:MM` |
| Saturdays | `/SC WEEKLY /D SAT /ST HH:MM` |
| 1st of each month | `/SC MONTHLY /D 1 /ST HH:MM` |

Settle can use direct python (no wrapper) if you prefer:

```powershell
schtasks /Create /TN "\Edge-Radar\Hourly-Settle" `
  /TR "<REPO_ROOT>\.venv\Scripts\python.exe <REPO_ROOT>\scripts\kalshi\kalshi_settler.py settle" `
  /SC HOURLY /ST 00:35 /F
```

> **Running this from Git Bash instead of PowerShell?** Prefix every `schtasks` call with `MSYS_NO_PATHCONV=1` or Git Bash mangles the `/TN` path into a filesystem path. See [Setup Gotchas](#setup-gotchas-for-future-reference).

### Minimal viable automation

The full pipeline is ~20 tasks; you don't need them all. **Minimal core = `All-Sports-SameDay-Execution` + `Hourly-Settle`** (execute today's games, settle them as they finish). Add the weekly `Calibration` for model health, then layer in the email actions and the midday/late/next-day runs as you trust the pipeline. Always run the [Dry-Run Testing Workflow](#dry-run-testing-workflow) before any execute task can place real money.

---

## Active Tasks (State: Ready)

### 0a. `Daily-Summary` — Daily 4:50 AM PST (7:50 AM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\maintenance\daily_summary.bat` |
| **Runs** | `daily_summary.py --save` |
| **Purpose** | Morning P&L digest — yesterday's settled W/L/$ (rolling 24h) + per-sport breakdown + currently open exposure + today's pending positions + live Kalshi balance + 7-day rolling context |
| **Report output** | `reports\Performance\daily_summary_YYYY-MM-DD.md` |
| **Empty-day behavior** | Still produces a report — proof-of-life pattern matches the SameDay email policy |
| **Email** | Action 2: `render_report_email.py daily-summary` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Daily Summary`, log `logs/email_daily_summary.log` |

**Why 4:50 AM PST:** After the overnight `Hourly-Settle` passes (yesterday's bets are settled in the log) and before the 5:05 AM PST `All-Sports-SameDay-Execution` (so the "Open Exposure" view reflects overnight carry rather than today's new fills mixing in). The email goes out as soon as the digest is written, so "what happened yesterday" arrives ahead of "what I bet today".

---

### ~~0b. `Email-Daily-Summary`~~ — MERGED 2026-09-23 into #0a

Now the second action of [`Daily-Summary`](#0a-daily-summary--daily-450-am-pst-750-am-et).

---

### 1. `All-Sports-SameDay-Execution` — Daily 5:05 AM PST (8:05 AM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\same_day_executions\same_day_execute.bat` |
| **Flags** | `--unit-size 1 --max-bets 7 --min-bets 1 --budget 12% --date today --exclude-open` |
| **Purpose** | Places bets on today's games across NBA/NHL/MLB/NFL |
| **Report output** | `reports\Sports\schedulers\same-day-executions\YYYY-MM-DD_sports_execution.md` |
| **Max exposure** | 12% of bankroll / 7 bets |
| **Risk gates** | All 11 enforced (see `CLAUDE.md`) |
| **Email** | Action 2: `render_report_email.py same-day` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Same Day Execution Report`, log `logs/email_sameday.log` |

**Why 5:05 AM PST:** MLB starters announced, NHL morning skate behind us, weather forecasts stabilized, Kalshi liquidity building, before sharp money fully hits market. Sweet spot for lineup/weather/pitcher freshness.

---

### ~~2. `Email-SameDay`~~ — MERGED 2026-09-23 into #1

Now the second action of `All-Sports-SameDay-Execution`. No report → no email (exit 2), so a failed scan never sends a stale one.

---

### 3. `All-Sports-NoDateFilter-Midday-Execution` — Daily 11:00 AM PST (2:00 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\no_date_filter_executions\no_date_filter_execution_midday.bat` |
| **Flags** | `--unit-size 1 --max-bets 5 --min-bets 1 --budget 8% --exclude-open` (no `--date`) |
| **Purpose** | Midday wide-net scan across all sports + all dates. The only NoDateFilter run after the Mon/Thu 5:20 AM task was retired 2026-05-17 |
| **Report output** | `reports\Sports\schedulers\no-date-filter-midday-executions\YYYY-MM-DD_sports_execution.md` |
| **Max exposure** | 8% of bankroll / 5 bets |
| **Email** | Action 2: `render_report_email.py nodatefilter-midday` → `mikeschecht@gmail.com`, subject `Edge-Radar \| NoDateFilter Midday Execution Report`, log `logs/email_nodatefilter_midday.log` |

**Why daily 11:00 AM PST (2:00 PM ET):** Per `timing-analysis-2026-05-17.md`, the data showed `NoDateFilter` (no date filter, all sports, all dates) hits 100% of the time while `SameDay` (`--date today`) is empty 71% of mornings. The 2026-05-05 datapoint was decisive: at 15:37 PT SameDay returned 0 bets, at 15:41 PT NoDateFilter returned 6 — same Kalshi book, same minute. The slate-width filter is the bottleneck, not the time of day. 11:00 AM also picks up MLB pitcher confirmations (~10-11 AM ET) and NBA/NHL morning-skate news that the 5:05 AM SameDay run misses.

**Replaces the Mon/Thu 5:20 AM `All-Sports-NoDateFilter-Execution`** (retired 2026-05-17). The prior cadence covered only 2 days/week with a redundant scope to what daily Midday now covers. Daily Midday + Gate 5 (`--exclude-open`) + Gate 7 (series dedup) is the cleaner design.

---

### ~~4. `Email-NoDateFilter-Midday`~~ — MERGED 2026-09-23 into #3

---

### 5. `All-Sports-SameDay-Late-Execution` — Daily 2:00 PM PST (5:00 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\same_day_executions\same_day_execute_late.bat` |
| **Flags** | `--unit-size 1 --max-bets 4 --min-bets 1 --budget 5% --date today --exclude-open` |
| **Purpose** | Late same-day scan — catches late-breaking news on tonight's games |
| **Report output** | `reports\Sports\schedulers\same-day-late-executions\YYYY-MM-DD_sports_execution.md` |
| **Max exposure** | 5% of bankroll / 4 bets (third bite at the same-day apple after 5:05 AM + 11:00 AM) |
| **Email** | Action 2: `render_report_email.py same-day-late` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Same-Day Late Execution Report`, log `logs/email_sameday_late.log` |

**Why daily 2:00 PM PST (5:00 PM ET):** Catches NBA/NHL pre-game news on evening games — scratches, goalie confirmations, mid-afternoon sharp-money moves. The `--date today` filter is intentional: this scan is specifically chasing late-breaking developments on tonight's slate, not the broader week. Smallest budget cap of any execute task because it's the most speculative — first 2-4 weeks of data will show whether it's pulling its weight or mostly returning Gate-5-blocked noise.

**Note on experimental status:** Marked Tier 2 ("moderate confidence") in the timing-analysis recommendation. The manual midday SameDay runs that informed the decision were mixed (only 1/4 hit). If the first 2-4 weeks show consistently empty reports OR consistently duplicate Gate-5-blocked markets, disable.

---

### ~~6. `Email-SameDay-Late`~~ — MERGED 2026-09-23 into #5

---

### 7. `All-Sports-NextDay-Execution` — Sun-Thu 8:30 PM PST (11:30 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sun, Mon, Tue, Wed, Thu |
| **Script** | `scripts\schedulers\next_day_executions\next_day_execute.bat` |
| **Flags** | `--unit-size 1 --max-bets 6 --min-bets 1 --budget 12% --date tomorrow --exclude-open` |
| **Purpose** | Locks in early lines for tomorrow's games |
| **Report output** | `reports\Sports\schedulers\next-day-executions\YYYY-MM-DD_sports_execution.md` |
| **Max exposure** | 12% of bankroll / 6 bets |
| **Email** | Action 2: `render_report_email.py next-day` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Next Day Edge Report`, log `logs/email_nextday.log` |

**Why Sun-Thu 8:30 PM PST (11:30 PM ET):** Shifted from 6:00 PM 2026-05-17 per `timing-analysis-2026-05-17.md`. Previous 6:00 PM PT (9:00 PM ET) timing had a 43% empty-report rate — many sportsbooks hadn't posted tomorrow's lines by 9 PM ET, especially Kalshi tomorrow markets which thin out for next-day events. 11:30 PM ET catches: full posting of next-day lines by Vegas books, fuller Kalshi liquidity after East Coast slate completes, West Coast NBA/NHL games winding down.

Sun-Thu only — Fri + Sat still skipped so the Sunday-morning 5:05 AM run handles Sunday NFL with fresher data.

---

### ~~8. `Email-NextDay`~~ — MERGED 2026-09-23 into #7

---

### ~~9. `NightlySettle`~~ — REMOVED 2026-09-23

Ran `kalshi_settler.py settle` daily at 11:00 PM — the same command as [#22 `Hourly-Settle`](#22-hourly-settle--every-hour-at-35), whose 10:35 and 11:35 PM passes cover the slot. Kept after 2026-07-20 only as a validation-week backstop. Recreate the settle job with `python scripts/schedulers/automation/install_windows_task.py install settle` (which now registers the hourly task).

---

### 10. `Reconcile` — Daily 11:30 PM PST (2:30 AM ET next day)

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\maintenance\reconcile.bat` |
| **Runs** | `kalshi_settler.py reconcile` |
| **Purpose** | Compares local trade log against Kalshi API, flags discrepancies |
| **Dependencies** | Runs AFTER the 10:35 PM `Hourly-Settle` pass (55-min buffer) |

**Why after the 10:35 PM settle:**
- Lets that settle fully complete (typical 2-5 min runtime)
- Reconcile checks for drift that settle would have fixed — better data if settle ran first
- Any drift caught here signals either: missed settlement, API lag, or local-log corruption

---

### 11. `Calibration` — Sun 7:00 PM PST (10:00 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sun |
| **Script** | `scripts\schedulers\maintenance\calibration.bat` |
| **Runs** | `model_calibration.py --days 7 --save` |
| **Purpose** | Weekly Brier score refresh, per-sport calibration curves, dimension breakdowns |
| **Output** | `reports/` calibration report |

**What it reports:**
- Brier score (predicted probability vs realized outcome)
- Calibration curve: predicted win rate vs actual win rate by decile
- Per-sport, per-confidence, per-edge-bucket breakdowns
- Prioritized recommendations (e.g., "NBA edge floor should move to 10%")

**Why Sunday 7 PM:** Full week of settled trades available; captures NBA Sunday afternoon + NFL Sunday + weekend MLB; runs before Monday's weekly-broad execute so any calibration recommendations can be applied immediately.

---

### 12. `Backtest` — Sun 7:30 PM PST (10:30 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sun |
| **Script** | `scripts\schedulers\maintenance\backtest.bat` |
| **Runs** | `backtester.py --simulate --save` |
| **Purpose** | Equity curve, max drawdown, Sharpe, strategy comparison |
| **Dependencies** | Runs AFTER Calibration (fresh data) |

**What it reports:**
- Equity curve and running drawdown
- Win/lose streaks
- Profit factor, Sharpe ratio, ROI
- Breakdowns by sport, category (ML/Spread/Total), confidence, edge bucket
- Strategy simulation: compares filter strategies (e.g., "confidence >= medium only" vs "edge >= 10% only")

---

### 13. `Weekly-Analysis` — Sun 11:45 PM PST (2:45 AM ET Mon)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sun |
| **Script** | `scripts\schedulers\maintenance\weekly_analysis.bat` |
| **Runs** | `betting_analysis.py --days 7 --save` |
| **Purpose** | End-of-week 7-day performance review driving the `/edge-radar-analysis` skill output |
| **Output** | `reports\Performance\betting_analysis_YYYY-MM-DD_7d.md` |
| **Dependencies** | Runs AFTER `Reconcile` (11:30 PM) + the 11:35 PM `Hourly-Settle` — 10-min buffer |
| **Email** | Action 2: `render_report_email.py weekly-analysis` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Weekly Performance Analysis`, log `logs/email_weekly_analysis.log` |

**What it reports:** Headline stats, by-sport / by-category / by-side (YES/NO) / edge buckets / confidence / market price breakdowns, calibration, longshots, win-loss streaks, daily P&L, and full trade ledger.

**Why Sun 11:45 PM:**
- Reconcile + Hourly-Settle have just completed — trade log is fresh and drift-checked
- Captures the full week including Sunday NFL/NBA/MLB
- The report's filename carries the UTC date (tomorrow's, at 11:45 PM PT) — the emailer picks the newest fresh file, not today's name

---

### ~~14. `Email-Weekly-Analysis`~~ — MERGED 2026-09-23 into #13

Now the second action of `Weekly-Analysis`. It sends the rendered report only — the model-written summary bullets the old `claude -p` email added are gone.

---

### 15. `MonthlyCalibration` — REMOVED 2026-07-31

Registered as a monthly (1st, 2:00 AM PST) run of
`.venv\Scripts\python.exe scripts\kalshi\model_calibration.py --days 30 --save`.

**It never once executed** — `Last Run Time` was still the Task Scheduler sentinel
`11/30/1999` when it was removed, with `Last Result 267011` ("task has not yet run").
Every calibration this repo has ever performed came from the weekly `Calibration`
task (#11) instead.

Removed as cruft once #11's window was widened to `--days 30`, since the two then did
exactly the same job and the C8 loop is stateless (a redundant run is a no-op). To
recreate it if ever wanted:

```powershell
schtasks /Create /TN "\Edge-Radar-MikesAILab\MonthlyCalibration" /SC MONTHLY /D 1 /ST 02:00 ^
  /TR "'D:\...\Edge-Radar\.venv\Scripts\python.exe' 'D:\...\Edge-Radar\scripts\kalshi\model_calibration.py' --days 30 --save"
```

---

### 18. `WeeklyAccountGraph` — Sun 9:00 AM PST (12:00 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sun |
| **Executable** | `.venv\Scripts\python.exe` (direct invocation — no .bat wrapper) |
| **Arguments** | `scripts\schedulers\automation\refresh_account_graph.py` |
| **Purpose** | Keeps the private account-growth graph current. Pulls the live Kalshi snapshot and regenerates the interactive HTML + static PNG. Never published — the graph carries real balance figures and the repo is public (see CHANGELOG 2026-09-07) |
| **Output** | `docs/my-documents/account-graph/latest/` (local, gitignored); log at `logs/account_graph_refresh.log` |
| **Install** | `python scripts/schedulers/automation/install_windows_task.py install account-graph` |

**Why Sunday 9:00 AM PST:** Weekend morning, after Saturday's slate has settled (overnight `Hourly-Settle` passes) and well clear of the Sun 5:05 AM SameDay execute. Once-a-week is plenty for a balance chart.

**Why a `gh` push instead of a normal commit:** generation must run locally (needs the `.env` Kalshi keys + the gitignored local settlements ledger), but the Pages deploy only watches `master`. Pushing the single file via `gh api PUT .../contents/...` updates `master` directly without touching the `mike_desktop` working branch or requiring a PR. `.claude/html/account-*.html` is gitignored so the file is managed solely by this task and never collides with branch PRs. The push is best-effort — if `gh` is unavailable the local graph still regenerates and the failure is logged.

**Privacy note:** the published graph shows **real dollar figures** (balance, deposit, P&L) on a public, unauthenticated site. It's at an unguessable filename with a `noindex, nofollow` meta tag — *lightly hidden, not access-controlled*. Treat the graph as public.

---

### 19. `Weekly-Futures-Execution` — Sat 9:00 AM PST (12:00 PM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | Weekly Sat |
| **Script** | `scripts\schedulers\futures_executions\weekly_futures_execute.bat` |
| **Runs** | `scan.py futures --unit-size 1 --max-bets 3 --min-bets 1 --budget 10% --exclude-open --save --report-dir "reports\Futures\schedulers" --execute` |
| **Purpose** | First **futures** automation — scans championship/outright winner markets (NFL Super Bowl, NBA Finals, NHL Stanley Cup, MLB World Series, NCAAB MOP, golf majors) and executes top picks. Offseason series with no Odds API outright data are skipped automatically; golf only prices the 4 majors during their play weeks |
| **Output** | `reports\Futures\schedulers\YYYY-MM-DD_futures_scan.md` + portfolio status before/after |
| **Email** | Action 2: `render_report_email.py weekly-futures` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Weekly Futures Execution Report`, log `logs/email_futures.log` |

**Why Saturday 9:00 AM PST:** the lightest day in the schedule (no other Edge-Radar task fires Saturday morning), so no contention. Outright lines are posted and sharp by mid-morning, and golf majors (Thu–Sun) are mid-tournament. Once-a-week matches the slow-moving nature of futures.

**Why conservative sizing (10% budget / max 3 / unit $1):** futures boards are thin and longshot-heavy, and the game-tuned gates (composite ≥ 6.0, `MIN_MARKET_PRICE` floor, NO-favorite guard) reject most outright candidates — so this task often places **0 bets**, by design. All standard risk gates + the `MAX_BET_SIZE` cap apply. `--min-bets 1` aborts cleanly when nothing qualifies (no over-concentration).

**Install (one-time, from Git Bash):**
```bash
MSYS_NO_PATHCONV=1 schtasks /create /tn "\Edge-Radar\Weekly-Futures-Execution" \
  /tr "D:\AI_Agents\Specialized_Agents\Edge_Radar\scripts\schedulers\futures_executions\weekly_futures_execute.bat" \
  /sc weekly /d SAT /st 09:00 /f
```

**Validated 2026-06-20 (install day):** registered (State=Ready, DaysOfWeek=64=Sat, next run 2026-06-27 9:00 AM), fired via `schtasks /run` → `LastTaskResult=0`. The day's 4 futures candidates (NFL LAR, MLB NYY, 2× U.S. Open golf) were all correctly rejected by the gates (score/price) → **0 bets placed**, balance untouched — a safe live end-to-end test.

**Proof-of-life on empty weeks:** futures boards are thin, so most weeks place 0 bets. `futures_edge.py` **always** writes a report on `--save` (since 2026-06-20) — an empty "0 orders" report when nothing clears — so the email goes out every week.

**WARNING:** places live orders when `DRY_RUN=false`. Verify `.env` before relying on it.

---

### ~~20. `Email-Weekly-Futures`~~ — MERGED 2026-09-23 into #19

---

### 21. `Daily-Polymarket-Execution` — Daily 9:40 AM PST (12:40 PM ET)

> **Renamed 2026-07-23** from `Daily-Polymarket-DryRun`. The task passes `--execute` and places real orders; the old name asserted the opposite.

| Property | Value |
|:---------|:------|
| **Schedule** | Daily |
| **Script** | `scripts\schedulers\polymarket_scans\daily_polymarket_scan.bat` |
| **Runs** | `scan.py polymarket --filter all --min-edge 0.01 --top 40 --max-bets 2 --budget 10% --save --execute` (widened 2026-07-20 from `--filter futures`; `--execute` + batch caps added 2026-07-23) |
| **Purpose** | ⚠️ **Places real orders.** Polymarket scan: championship futures (NFL, MLB World Series, NBA, NHL Stanley Cup) **plus PM1d per-game markets** (MLB/NFL/NBA/NHL moneyline, run-line spread, game total — priced by the same calibrated consensus model as Kalshi sports). Appends every run — timestamp, filter, opportunity count, each opportunity with its preflight gate verdict and `executable` flag, **including 0-opportunity runs** — to the evidence log (`--save` runs outside the execute branch, so the funnel is recorded either way). `--min-edge 0.01` widens what gets *recorded*; the risk gates still enforce the real floors (3% edge). **Only futures are orderable** — Gamma-sourced games carry no US `market_slug` and are auto-excluded from execution |
| **Output** | `data\polymarket\dryrun_log.jsonl` (append-only evidence) + `reports\Polymarket\YYYY-MM-DD_futures_polymarket_scan.md` (only when rows surface) |
| **Log** | `logs\polymarket_dryrun_scan.log` |
| **Email** | Action 2: `render_report_email.py polymarket` → `mikeschecht@gmail.com`, subject `Edge-Radar \| Daily Polymarket Execution Report`, log `logs/email_polymarket_dryrun.log` (name kept — history predates the rename). Always leads with an **Execution outcome** section: the last run of `logs\polymarket_dryrun_scan.log` minus INFO lines. On 0-opportunity days (no report written) it still sends, as proof-of-life. Replaced `Email-Polymarket-Execution` (#23) 2026-09-23 |
| **Cost** | ~4 Odds API requests per run (one per active outright sport key) |

**Why daily 9:40 AM PST:** quiet slot — after the 5:05 morning run, before the 11:00 midday run, and clear of Saturday's 9:00 futures run. Morning outright lines are posted and sharp. Daily (vs the weekly Kalshi futures cadence) because the edge-proving window wants sample size, and a read-only run is cheap.

**Places REAL orders (since 2026-07-23):** the task passes `--execute`, and both `DRY_RUN` and `POLYMARKET_DRY_RUN` are `false` in `.env`, so any row clearing the risk gates becomes an unattended wager. Batch capped at `--max-bets 2 --budget 10%`. To halt this venue without touching Kalshi, set `POLYMARKET_DRY_RUN=true`. The `.bat` sets `PYTHONIOENCODING=utf-8` — required because the rich table output contains Unicode that crashes cp1252 when the console is redirected to the log file.

**Install (one-time, from PowerShell):**
```powershell
schtasks /Create /TN "\Edge-Radar-MikesAILab\Daily-Polymarket-Execution" `
  /TR "D:\AI_Agents\Projects\Mikes_AI_Lab\Repos\AI-Automation-Tools\Live_Apps\Edge-Radar\scripts\schedulers\polymarket_scans\daily_polymarket_scan.bat" `
  /SC DAILY /ST 09:40 /F
```

**Re-validated 2026-07-23 (post-rename):** re-registered as `Daily-Polymarket-Execution` preserving the trigger/principal, fired via `Start-ScheduledTask` → `LastTaskResult=0`; 4 opportunities risk-checked, **0 orders placed** (all rejected on `edge_below_threshold`, 1.1–2.6% vs the 3.0% floor), evidence log appended.

**Validated 2026-07-20 (install day):** registered (State=Ready, next run 2026-07-21 9:40 AM), fired via `Start-ScheduledTask` → `LastTaskResult=0`; evidence record appended to `dryrun_log.jsonl` and the day's report written (1 opportunity: NBA Spurs +4.0%, low confidence, correctly gated on score → 0 would-bet).

---

### 22. `Hourly-Settle` — Every hour at :35

| Property | Value |
|:---------|:------|
| **Schedule** | Hourly (`/SC HOURLY /MO 1 /ST 00:35`) |
| **Executable** | `.venv\Scripts\python.exe` (direct invocation — no .bat wrapper) |
| **Arguments** | `scripts\kalshi\kalshi_settler.py settle` |
| **Purpose** | U1: settle throughout the day instead of once at 11 PM. Keeps `data/history` fresh so **Gate 1 (daily loss limit)** sees intraday settlements, positions clear as games end, and R4 resting-order cleanup runs timely |
| **Why now** | Enabled by **M2** (2026-07-20): the cross-process trade-log lock + merge-safe `append_trades` make a settle that overlaps an execute task merge instead of clobber — exactly the race that made hourly settling unsafe before |
| **Why :35** | The only minute slot clear of every existing task (:00 executes, :05 SameDay, :30 Reconcile/NextDay, :40 Polymarket, :45 Weekly-Analysis, :50 Daily-Summary; emails ride their scan task since 2026-09-23) |
| **NightlySettle** | Kept as belt-and-suspenders during validation, **retired 2026-09-23** — settle is idempotent, so its 11:00 PM run only ever found nothing new after the 10:35 PM sweep |

**Install (one-time, from PowerShell):**
```powershell
schtasks /Create /TN "\Edge-Radar\Hourly-Settle" `
  /TR "D:\AI_Agents\Specialized_Agents\Edge_Radar\.venv\Scripts\python.exe D:\AI_Agents\Specialized_Agents\Edge_Radar\scripts\kalshi\kalshi_settler.py settle" `
  /SC HOURLY /MO 1 /ST 00:35 /F
```

**Re-validated 2026-07-23 (post-rename):** re-registered as `Daily-Polymarket-Execution` preserving the trigger/principal, fired via `Start-ScheduledTask` → `LastTaskResult=0`; 4 opportunities risk-checked, **0 orders placed** (all rejected on `edge_below_threshold`, 1.1–2.6% vs the 3.0% floor), evidence log appended.

**Validated 2026-07-20 (install day):** registered, fired via `Start-ScheduledTask` → `LastTaskResult=0`, next fire on the :35.

---

### ~~23. `Email-Polymarket-Execution`~~ — MERGED 2026-09-23 into #21

Now the second action of `Daily-Polymarket-Execution`; its still-true behaviour (execution-outcome lead, proof-of-life on empty days) is in that section.

---

### 17. `U2-Review` — One-shot 2026-05-14 7:00 AM PT (10:00 AM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | One-time (`/sc once /sd 05/14/2026 /st 07:00`) |
| **Script** | `scripts\schedulers\maintenance\u2_2week_review.bat` |
| **Runs** | `u2_2week_review.py` |
| **Purpose** | Post-ship review of U2 daily-summary digest (~2 weeks after 2026-04-30 ship). Local pass scans `reports/Performance/daily_summary_*.md` for the last 14 days to surface firing-reliability + section coverage (which sections were consistently empty across the window). Then spawns a `claude --dangerously-skip-permissions -p` subprocess (the pattern the email tasks used until 2026-09-23) to do a code-review pass on `scripts/kalshi/daily_summary.py` + tests, with explicit instructions to be opinionated about what to drop. Combines both into a single recommendation report with an operational checklist for the user to fill in (which sections they actually read each morning, any rendering issues, anything missing from the digest) |
| **Output** | `reports\Performance\u2_2week_review_YYYY-MM-DD.md` |

**Why 2026-05-14 7:00 AM PT:** ~2 weeks after U2 ship (2026-04-30) — long enough for ~14 actual digest files to exist (firing-reliability signal) and a meaningful operational pattern to emerge, before the format choices calcify. Off-peak local time, no conflict with any daily/weekly task. One-shot — fires once and `Status: Ready` flips after.

**Migrated from a remote routine** (`trig_01Q6iNTVkob15MewHYS5CKYH`, now disabled) per the established pattern (see "One-shot review pattern" in `project_scheduled_tasks.md` memory + R8-Review precedent). The local-script approach is strictly better here because the remote agent literally couldn't see `reports/Performance/daily_summary_*.md` (gitignored) — the firing-reliability signal lives only on the user's machine.

**One-shot task management:** if 2026-05-14 fires before enough digest data has accumulated (e.g. user installed the Daily-Summary tasks late), re-arm with:

```bash
MSYS_NO_PATHCONV=1 schtasks /change /tn "\Edge-Radar\U2-Review" /sd <new-date> /st 07:00
```

Or delete entirely with `Unregister-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'U2-Review'`.

---

### 16. `R8-Review` — One-shot 2026-05-29 6:00 AM PT (9:00 AM ET)

| Property | Value |
|:---------|:------|
| **Schedule** | One-time (`/sc once /sd 05/29/2026 /st 06:00`) |
| **Script** | `scripts\schedulers\maintenance\r8_review.bat` |
| **Runs** | `r8_cross_category_review.py` |
| **Purpose** | Post-hoc A/B review of R8 (cross-category dedup, shipped 2026-04-29). Slices `data/history/kalshi_settlements.json` into ML/Total/Spread cohorts per `(sport, game_id)`, simulates the R8-on outcome (highest-edge bet kept), and recommends per-sport FLIP ON / FLIP OFF / NEED MORE DATA |
| **Output** | `reports\Performance\R8_cross_category_review_YYYY-MM-DD.md` |

**Why 2026-05-29 6:00 AM PT:** ~30 days after R8 ship (2026-04-29) — long enough for a meaningful cohort sample, before the change is "old news". Off-peak local time, no conflict with any daily/weekly task. One-shot — fires once and `Status: Ready` flips after.

**Recommendation rules** (encoded in the script):
- **FLIP ON** — status-quo cohort ROI ≤ 0 AND R8-on - status-quo > 5pp AND n_xcat ≥ 10
- **NEED MORE DATA** — n_xcat < 10
- **FLIP OFF (keep default)** — everything else

The report includes an `.env` snippet listing the exact `CROSS_CATEGORY_DEDUP_<SPORT>=true` lines to paste in for sports that meet the FLIP ON bar. User reviews and applies manually.

**One-shot task management:** if 2026-05-29 produces NEED MORE DATA across the board, re-arm with:

```bash
MSYS_NO_PATHCONV=1 schtasks /change /tn "\Edge-Radar\R8-Review" /sd <new-date> /st 06:00
```

Or delete entirely with `Unregister-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'R8-Review'`.

---

## Disabled Tasks (retained for reference)

These remain in `\Edge-Radar\` but are not enabled. They were part of prior experiments or replaced by consolidated equivalents.

| Task | Script | Why disabled |
|:-----|:-------|:-------------|
| `All-Sports-NoDateFilter-Scan` | `no_date_filter_scan.bat` | Scan-only variant; execution variant is what runs |
| `All-Sports-SameDay-Scan` | `same_day_scan.bat` | Scan-only variant; execution variant is what runs |
| `MLB-NextDay-Scan` | `mlb_morning_scan.bat` | Per-sport variant; replaced by consolidated `All-Sports-NextDay-Execution` |
| `NBA-NextDay-Scan` | `nba_morning_scan.bat` | Per-sport variant; replaced |
| `NFL-NextDay-Scan` | `nfl_morning_scan.bat` | Per-sport variant; replaced |
| `NHL-NextDay-Scan` | `nhl_morning_scan.bat` | Per-sport variant; replaced |

Keep these in place — useful reference for how to structure per-sport scans if that pattern is ever needed again.

---

## Daily / Weekly Timeline

Every task below except `Reconcile`, `Calibration` and `Backtest` emails its own report as a second action (since 2026-09-23), so there are no separate email lines.

### A typical Mon-Thu
```
05:05 AM  All-Sports-SameDay-Execution         → bets today's NBA/MLB/NHL games
09:40 AM  Daily-Polymarket-Execution           → PM scan + EXECUTE (places real orders)
11:00 AM  All-Sports-NoDateFilter-Midday-Exec  → midday wide-net (no date filter)
02:00 PM  All-Sports-SameDay-Late-Execution    → late same-day catch-up
08:30 PM  All-Sports-NextDay-Execution         → bets tomorrow's games
11:30 PM  Reconcile                            → verify local vs API
```

### A typical Sunday
```
05:05 AM  All-Sports-SameDay-Execution  (Sunday's NBA/MLB/NFL)
09:40 AM  Daily-Polymarket-Execution    (PM scan + EXECUTE)
11:00 AM  All-Sports-NoDateFilter-Midday-Execution
02:00 PM  All-Sports-SameDay-Late-Execution
07:00 PM  Calibration                   (weekly Brier refresh)
07:30 PM  Backtest                      (weekly strategy review)
08:30 PM  All-Sports-NextDay-Execution  (Monday's games)
11:30 PM  Reconcile
11:45 PM  Weekly-Analysis
```

### A typical Fri
```
05:05 AM  All-Sports-SameDay-Execution
09:40 AM  Daily-Polymarket-Execution        (PM scan + EXECUTE)
11:00 AM  All-Sports-NoDateFilter-Midday-Execution
02:00 PM  All-Sports-SameDay-Late-Execution
          (All-Sports-NextDay-Execution skipped — Sunday morning run will handle Sunday NFL)
11:30 PM  Reconcile
```

### A typical Sat
```
05:05 AM  All-Sports-SameDay-Execution
09:00 AM  Weekly-Futures-Execution          (futures scan + execute; often 0 bets)
09:40 AM  Daily-Polymarket-Execution        (PM scan + EXECUTE)
11:00 AM  All-Sports-NoDateFilter-Midday-Execution
02:00 PM  All-Sports-SameDay-Late-Execution
          (All-Sports-NextDay-Execution skipped — Sunday morning run will handle Sunday NFL)
11:30 PM  Reconcile
```

---

## Daily Bet Count Estimate

| Day | Max new bets | Notes |
|:----|:-------------|:------|
| Mon-Thu | **7 (SameDay) + 5 (Midday-NoDateFilter) + 4 (Late-SameDay) + 6 (NextDay) = 22** | Gate 7 series dedup + `--exclude-open` reduce practical count significantly |
| Fri | **7 + 5 + 4 = 16** | (NextDay skipped Fri/Sat) |
| Sat | **7 + 5 + 4 + 3 (Weekly-Futures) = 19** | NextDay skipped; futures rarely fills (gates reject most outrights) |
| Sun | **7 + 5 + 4 + 6 = 22** | |

Hard ceiling: Gate 2 (max open positions = 50) prevents runaway accumulation. Settle at 11 PM clears ~50% of opens each night. The Midday-NoDateFilter (8%) and Late-SameDay (5%) tasks use smaller budgets than the morning SameDay (12%) and evening NextDay (12%) runs to preserve daily-cap headroom.

---

## Manual Trigger Commands

Run any task immediately via Git Bash (prepend `MSYS_NO_PATHCONV=1` to prevent path translation):

```bash
# Daily summary digest
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Daily-Summary"   # generates + emails

# Betting execute tasks (each emails its report as action 2)
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\All-Sports-SameDay-Execution"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\All-Sports-NoDateFilter-Midday-Execution"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\All-Sports-SameDay-Late-Execution"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\All-Sports-NextDay-Execution"

# Email only, no scan (sends the newest report under 3h old; add --dry-run out.html to preview)
.venv/Scripts/python.exe scripts/schedulers/automation/render_report_email.py same-day

# Polymarket scan + EXECUTE (places real orders) + its email
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar-MikesAILab\Daily-Polymarket-Execution"

# Maintenance
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Hourly-Settle"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Reconcile"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Calibration"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Backtest"
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Weekly-Analysis"   # generates + emails

# One-shot reviews (can be triggered manually any time)
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\R8-Review"      # fires 2026-05-29
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\U2-Review"      # fires 2026-05-14
```

From PowerShell (no prefix needed):

```powershell
Start-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'All-Sports-NextDay-Execution'
```

---

## Management Commands

### List all tasks in folder
```powershell
Get-ScheduledTask -TaskPath '\Edge-Radar\' | Select-Object TaskName, State | Format-Table
```

### See next run time + last result
```powershell
Get-ScheduledTask -TaskPath '\Edge-Radar\' | ForEach-Object {
  $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath
  [PSCustomObject]@{
    Name = $_.TaskName
    State = $_.State
    NextRun = $info.NextRunTime
    LastRun = $info.LastRunTime
    LastResult = $info.LastTaskResult  # 0 = success
  }
} | Sort-Object NextRun | Format-Table -AutoSize
```

### Disable a task (doesn't delete)
```powershell
Disable-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'All-Sports-NextDay-Execution'
```

### Enable a task
```powershell
Enable-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'All-Sports-NextDay-Execution'
```

### View full task definition (XML)
```powershell
Export-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'All-Sports-NextDay-Execution'
```

### Delete a task
```powershell
Unregister-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'TaskName' -Confirm:$false
```

---

## Wrapper Scripts (`scripts/schedulers/maintenance/`)

Created 2026-04-22 for maintenance tasks that need consistent CWD + venv python:

| File | Contents |
|:-----|:---------|
| `settle.bat` | `cd /d D:\...\Edge_Radar && .venv\Scripts\python.exe scripts\kalshi\kalshi_settler.py settle` |
| `reconcile.bat` | Same pattern, runs `reconcile` |
| `calibration.bat` | Runs `model_calibration.py --days 7 --save` |
| `backtest.bat` | Runs `backtester.py --simulate --save` |
| `weekly_analysis.bat` | Runs `betting_analysis.py --days 7 --save` |
| `daily_summary.bat` | Runs `daily_summary.py --save` (morning P&L digest; the `Daily-Summary` task emails it as action 2) |
| `r8_review.bat` | Runs `r8_cross_category_review.py` (one-shot, scheduled 2026-05-29) |
| `u2_2week_review.bat` | Runs `u2_2week_review.py` (one-shot, scheduled 2026-05-14) |

**Note:** `Hourly-Settle` is set up with direct python invocation (no .bat wrapper). The wrappers exist for manual invocation convenience and to keep CWD + venv python consistent.

---

## Troubleshooting

### Email task logs

`render_report_email.py` appends one result line per run to a per-preset log — the same files the retired `.sh` scripts wrote, so history is continuous:

| Task (email is action 2) | Log file |
|:-----------|:---------|
| `Daily-Summary` | `logs/email_daily_summary.log` |
| `All-Sports-SameDay-Execution` | `logs/email_sameday.log` |
| `All-Sports-NoDateFilter-Midday-Execution` | `logs/email_nodatefilter_midday.log` |
| `All-Sports-SameDay-Late-Execution` | `logs/email_sameday_late.log` |
| `All-Sports-NextDay-Execution` | `logs/email_nextday.log` |
| `Daily-Polymarket-Execution` | `logs/email_polymarket_dryrun.log` (name kept — history predates the rename) |
| `Weekly-Futures-Execution` | `logs/email_futures.log` |
| `Weekly-Analysis` | `logs/email_weekly_analysis.log` |

`logs/` is gitignored. On a two-action task a non-zero `LastTaskResult` can come from either action, so read both the scan's own log/report and the email log before concluding which one failed.

### Exit code 2 (email action)

No fresh report: nothing in the preset's folder was modified within `--max-age-hours` (default 3), so the scan failed before its save step or wrote somewhere else. Nothing is sent, by design — a stale email is worse than none. (`polymarket` does not exit 2 here; no report is its normal zero-opportunity case, and it sends proof-of-life.)

### Send failures

A Resend error: `python scripts/custom/Python/send_report_email.py --check` probes the domain without spending quota; an unverified domain or a revoked `RESEND_API_KEY` fails every send. The email log line carries the error.

**Historical note (2026-06-15):** Two consecutive missing same-day emails (6/14, 6/15) traced to `edge_detector.py` only saving a report when at least one opportunity cleared the edge threshold (`if args.save and opportunities:`). Fixed so `--save` now **always** writes a report; a no-opportunity day emits an empty "0 orders" execution report.

### Exit code 267009 (still running)

`0x00041301` means the task hasn't finished yet. On a two-action task that includes the scan; the email action itself takes seconds.

### Exit code 267011 (never run)

`0x00041303` means the task has not yet been triggered since creation. Normal for newly-created tasks.

---

## Setup Gotchas (for future reference)

### Git Bash + schtasks
```bash
# WRONG — Git Bash translates /tn to a path
schtasks /create /tn "Foo" /tr "..." /sc daily /st 08:00
# → ERROR: Invalid argument/option - 'C:/Program Files/Git/create'

# CORRECT
MSYS_NO_PATHCONV=1 schtasks /create /tn "Foo" /tr "..." /sc daily /st 08:00
```

### Folder targeting
```bash
# WRONG — lands in root `\`
schtasks /create /tn "MyTask" ...

# CORRECT — lands in \Edge-Radar\
schtasks /create /tn "\Edge-Radar\MyTask" ...
```

### Email action invocation
The email is a second action on the scan task, not its own task. `schtasks /Create` can only make one action, so add it with PowerShell — see [Registering the tasks](#registering-the-tasks). Action form:

```
wscript.exe "<repo>\scripts\schedulers\run-hidden.vbs" "<repo>\.venv\Scripts\python.exe" "<repo>\scripts\schedulers\automation\render_report_email.py" <preset>
```

### Days of week bitmask
When checking task triggers via PowerShell, `DaysOfWeek` is a bitmask:

| Day | Bit | Value |
|:----|:----|:------|
| Sunday | 2^0 | 1 |
| Monday | 2^1 | 2 |
| Tuesday | 2^2 | 4 |
| Wednesday | 2^3 | 8 |
| Thursday | 2^4 | 16 |
| Friday | 2^5 | 32 |
| Saturday | 2^6 | 64 |

So `DaysOfWeek = 18` means `2 + 16` = Monday + Thursday.

---

## Dry-Run Testing Workflow

Before letting scheduled tasks place live bets:

1. **Set dry-run in `.env`:**
   ```
   DRY_RUN=true
   ```

2. **Suggested test order (safest first):**
   | Order | Task | Why |
   |:-----:|:-----|:----|
   | 1 | `Reconcile` | Read-only, quickest sanity check |
   | 2 | `Calibration` | Read-only, generates calibration report |
   | 3 | `Backtest` | Read-only, generates backtest report |
   | 4 | `Hourly-Settle` | Writes to local files but no external bets |
   | 5 | `All-Sports-NextDay-Execution` | Would place bets but dry-run blocks |
   | 6 | `All-Sports-NoDateFilter-Execution` | Biggest unknown, the new weekly broad |
   | 7 | `render_report_email.py <preset> --dry-run out.html` | Verify the email renders from an existing report, without sending |

3. **Manual trigger:** See "Manual Trigger Commands" section above.

4. **Check logs:** Scripts echo to console + write reports to `reports/Sports/schedulers/<mode>/`.

5. **Verify results:**
   - Execute tasks: report file exists, no positions opened (dry-run), exit code 0
   - Email tasks: email received, HTML renders correctly, report content matches file
   - Settle/Reconcile: no errors, no drift reported

6. **Flip to live:** When confident, set `DRY_RUN=false` in `.env`.

---

## Output File Structure

```
reports/Sports/schedulers/
├── same-day-executions/
│   └── 2026-04-22_sports_execution.md             ← Daily 5:05 AM
├── no-date-filter-executions/
│   └── 2026-04-22_sports_execution.md             ← (legacy, Mon/Thu task retired 2026-05-17)
├── no-date-filter-midday-executions/
│   └── 2026-05-17_sports_execution.md             ← Daily 11:00 AM (added 2026-05-17)
├── same-day-late-executions/
│   └── 2026-05-17_sports_execution.md             ← Daily 2:00 PM (added 2026-05-17)
└── next-day-executions/
    └── 2026-04-22_sports_execution.md             ← Sun-Thu 8:30 PM (shifted from 6:00 PM 2026-05-17)

reports/
├── Calibration/
│   ├── 2026-04-26_calibration_report.md  ← Sun 7:00 PM (weekly, 7-day)
│   └── 2026-05-01_calibration_report.md  ← 1st of month 2:00 AM (monthly, 30-day)
├── backtest/
│   └── 2026-04-26_backtest.md            ← Sun 7:30 PM
└── Performance/
    └── betting_analysis_2026-04-26_7d.md ← Sun 11:45 PM (weekly 7-day analysis)

data/
├── positions/open_positions.json          ← updated by execute + settle
└── history/2026-04-22_trades.json         ← updated by settle
```

---

## Email Delivery Architecture

```
Scan task, action 1: .bat runs the scan / execute
         ↓
Writes report file to reports/<...>/*.md
         ↓
Scan task, action 2 (runs even if action 1 exited non-zero)
         ↓
render_report_email.py <preset>
  picks newest report < 3h old  →  none? exit 2, no send (polymarket: proof-of-life)
  markdown → inline-styled HTML (markdown-it-py; tables byte-exact)
         ↓
send_report_email.py → Resend, from <YOUR_SENDER> → mikeschecht@gmail.com
         ↓
Subject: "Edge-Radar | <preset subject>"; result line → logs/email_*.log
```

**No buffer, no second clock:** the email fires the moment its scan finishes, so a slow scan can't race it and it can't drift from the scan across DST. **No model:** nothing in the path spawns a Claude session.

---

## Installing the Daily-Summary tasks (one-time)

> **Status:** `Daily-Summary` and `U2-Review` are **already installed** in `\Edge-Radar\` (`Email-Daily-Summary` was merged into `Daily-Summary` as its second action 2026-09-23). Snippets below are kept for reproducibility (e.g. reinstalling on a new machine, or after deleting + recreating to change the schedule).

Installed manually via `schtasks` (same pattern as the other maintenance tasks per R24c). Run once from Git Bash, then add the email action from PowerShell as in [Registering the tasks](#registering-the-tasks), with preset `daily-summary`:

```bash
# Daily-Summary — generates the digest at 4:50 AM PST
MSYS_NO_PATHCONV=1 schtasks /create /tn "\Edge-Radar\Daily-Summary" \
  /tr "D:\AI_Agents\Specialized_Agents\Edge_Radar\scripts\schedulers\maintenance\daily_summary.bat" \
  /sc daily /st 04:50 /f
```

**Verify:**
```powershell
(Get-ScheduledTask -TaskPath '\Edge-Radar\' -TaskName 'Daily-Summary').Actions | Format-Table Execute, Arguments   # expect 2 actions
```

**Dry-run test (won't place bets — read-only generators):**
```bash
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\Daily-Summary"
# wait ~5s, then verify report exists:
ls -la D:/AI_Agents/Specialized_Agents/Edge_Radar/reports/Performance/daily_summary_*.md
# the same run sends the email (action 2) — check logs/email_daily_summary.log
```

### Empty-day expected output (verified 2026-04-30 dry-run)

Running both (then separate) tasks manually on 2026-04-30 produced a successful email with three blank sections (Yesterday / Open Exposure / Pending Today) and one populated section (Context: balance + 7-day rolling). **This is correct** — proof-of-life pattern matches `feedback_sameday_empty_emails`. Causes that day:

- Trade log had been reset/wiped earlier (only 1 resting order, no filled positions)
- No settlements in the rolling 24h window
- No open positions on today's slate (follows from the above)

The Context section pulls from the historical `data/history/kalshi_settlements.json` (173 entries) so it's never empty. **If a week from now all three sections are still blank every morning,** that's a real signal — either the trade log isn't capturing fills, the settler isn't finding settlements, or the bet pipeline is paused. The U2-Review one-shot on 2026-05-14 (§ 15) surfaces that pattern explicitly via the section-coverage table.

### Bonus: install the one-shot U2-Review (fires 2026-05-14 at 7 AM PT)

> **Status (2026-04-30):** already installed. Snippet kept for reproducibility / re-arm on a new date.

Pairs with the Daily-Summary tasks — runs ~2 weeks later to scan the digest output and produce a recommendation report. Mirrors the R8-Review one-shot pattern.

```bash
MSYS_NO_PATHCONV=1 schtasks /create /tn "\Edge-Radar\U2-Review" \
  /tr "D:\AI_Agents\Specialized_Agents\Edge_Radar\scripts\schedulers\maintenance\u2_2week_review.bat" \
  /sc once /sd 05/14/2026 /st 07:00 /f
```

**Verify + dry-run test:**
```bash
MSYS_NO_PATHCONV=1 schtasks /query /tn "\Edge-Radar\U2-Review"
# Run now (works any time — the script is read-only):
MSYS_NO_PATHCONV=1 schtasks /run /tn "\Edge-Radar\U2-Review"
# Output: reports/Performance/u2_2week_review_YYYY-MM-DD.md
```

The script spawns a `claude --dangerously-skip-permissions -p` subprocess for the code-review pass (the pattern the email tasks used until 2026-09-23). To skip that and get only the local firing-reliability scan, run directly with `--skip-claude`:

```bash
.venv/Scripts/python.exe scripts/schedulers/maintenance/u2_2week_review.py --skip-claude
```

---

## References

- [`../../CLAUDE.md`](../../CLAUDE.md) — Master instructions, risk gates, risk limits
- [`../../skills/edge-radar/SKILL.md`](../../skills/edge-radar/SKILL.md) — Unified scanner reference (`/edge-radar`)
- [`../setup/AUTOMATION_GUIDE.md`](../setup/AUTOMATION_GUIDE.md) — One-command installer for the minimal core tasks
- [`../../.env.example`](../../.env.example) — Every tunable, including `NOTIFY_EMAIL` / `RESEND_FROM` for the email scripts

---

<p align="center">
  <a href="../README.md">Docs index</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="../setup/AUTOMATION_GUIDE.md">Automation Guide</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="../../CLAUDE.md">Risk gates</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="#-edge-radar-scheduled-tasks">Back to top</a>
</p>
