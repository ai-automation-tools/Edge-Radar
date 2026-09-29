# Upstreams

Every external service and library Edge-Radar depends on, what the code assumes about each,
and where to check whether that assumption still holds. The biweekly **Edge-Radar Upstream
Check** routine (`upstream/auto-*` PRs) works from this file. Keep it current by hand too:
a new API client is a new row.

**Money path** rows touch order placement, fills, settlement, or cash. The routine never
changes code on them. It opens a ROADMAP item and flags it in its PR body.

**Last checked** is filled in by the routine, and only with a date it actually read the
source. `—` means never checked.

## Execution venues (money path)

| Upstream | What the code assumes | Code | Check at | Last checked |
|:---|:---|:---|:---|:---|
| **Kalshi Trade API v2** | Base `api.elections.kalshi.com/trade-api/v2`; RSA-PSS request signing; fills and positions arrive as fixed-point strings (`fill_count_fp`, `position_fp`) and can be fractional (ROADMAP S28); the exchange is sharded (Crypto shard 2, Tennis and Baseball shard 3, since 2026-08-24) and cash does not follow the markets; the series tickers in the sport filters exist (`KXNCAAFGAME`, not `KXNCAAFBGAME`); the fee schedule | `scripts/kalshi/kalshi_client.py`, `kalshi_executor.py`, `kalshi_settler.py`, `app/config.py` · reference: `docs/kalshi/kalshi-sports-betting/KALSHI_API_REFERENCE.md` | docs.kalshi.com (API reference and changelog); kalshi.com/docs/kalshi-fee-schedule.pdf | — |
| **Polymarket US retail API** | Base `api.polymarket.us`; Ed25519-signed requests (not the international EIP-712 / `py-clob-client` scheme); `minimumTradeQty` per market; US game markets are moneyline-only | `scripts/polymarket/polymarket_exec_client.py`, `polymarket_us_data.py`, `polymarket_futures_edge.py` · reference: `docs/polymarket/polymarket-api/POLYMARKET_API_REFERENCE.md` | polymarket.us/developer | — |

## Market data

| Upstream | What the code assumes | Code | Check at | Last checked |
|:---|:---|:---|:---|:---|
| **Polymarket Gamma API** | `gamma-api.polymarket.com`; events found by `tag_id` filtering and `/public-search`; game rows carry no US `market_slug` | `scripts/polymarket/polymarket_client.py` | docs.polymarket.com | — |
| **The Odds API v4** | `api.the-odds-api.com/v4`; the per-event endpoint puts `last_update` on markets, not bookmakers (S19); monthly per-key quota, keys rotated by `check_odds_keys.py` | `scripts/kalshi/edge_detector.py`, `futures_edge.py`, `scripts/shared/check_odds_keys.py` | the-odds-api.com/liveapi/guides/v4/ | — |
| **ESPN site API** *(unofficial, undocumented)* | `site.api.espn.com/apis/site/v2/sports/…` and `/apis/v2/sports/…` return the shapes the parsers read | `scripts/shared/line_movement.py`, `rest_days.py`, `team_stats.py` | No official docs. Check with one live unauthenticated GET per endpoint and compare the keys the parser reads | — |
| **MLB Stats API** *(public, undocumented)* | `statsapi.mlb.com/api/v1` standings and pitcher endpoints | `scripts/shared/pitcher_stats.py`, `team_stats.py` | One live GET; github.com/toddrob99/MLB-StatsAPI tracks changes | — |
| **NHL web API** *(public, undocumented)* | `api-web.nhle.com/v1/standings/now` | `scripts/shared/team_stats.py` | One live GET | — |
| **NWS API** | `api.weather.gov/gridpoints/…`; requires a `User-Agent` header | `scripts/prediction/weather_edge.py`, `scripts/shared/sports_weather.py` | weather.gov/documentation/services-web-api | — |
| **CoinGecko API v3** | `api.coingecko.com/api/v3` `simple/price` and `coins/`; free-tier rate limit | `scripts/prediction/crypto_edge.py` | docs.coingecko.com (changelog) | — |
| **Yahoo Finance chart** *(unofficial)* | `query1.finance.yahoo.com/v8/finance/chart/` | `scripts/prediction/spx_edge.py` | One live GET | — |
| **FRED API** | `api.stlouisfed.org/fred` | `scripts/prediction/companies_edge.py` | fred.stlouisfed.org/docs/api/fred/ | — |

## Notifications

| Upstream | What the code assumes | Code | Check at | Last checked |
|:---|:---|:---|:---|:---|
| **Resend** | REST `POST /emails` over `requests`, no SDK | `scripts/custom/Python/send_report_email.py` | resend.com/docs and resend.com/changelog | — |
| **Telegram Bot API** | `api.telegram.org/bot…` | `scripts/schedulers/automation/telegram_bot.py` | core.telegram.org/bots/api-changelog | — |

## Runtime and libraries

| Upstream | What the code assumes | Where | Check at | Last checked |
|:---|:---|:---|:---|:---|
| **Python** | 3.11+ | `pyproject.toml`, `CLAUDE.md` | devguide.python.org/versions (EOL dates) | — |
| **`requests`, `cryptography`, `pandas`, `scipy`, `rich`, `filelock`, `markdown-it-py`** | Floor pins (`>=`) in `requirements.txt`; `cryptography` does the RSA-PSS and Ed25519 signing | `requirements.txt` | PyPI release pages. Flag breaking majors and security advisories only | — |

*Planned, not built* (no row until code exists): Alpaca, Coinbase, Manifold.
