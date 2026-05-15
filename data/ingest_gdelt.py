"""GDELT 2.0 GKG → daily India macro/policy-narrative regime features.

WHY THIS EXISTS
---------------
The macro_regime classifier already gets the market/price dimension
numerically (India VIX, Nifty-vs-200DMA, FII flows). It is blind to the
*policy/narrative* dimension: tariff escalation, RBI commentary tone, budget
reception, govt-policy uncertainty. GDELT's GKG is empirically good at
exactly that and bad at market-technical shocks (validated 2026-05-15 on
COVID-2020 / election-2024 / budget-2025 / a baseline day). So it is a
*complementary qualitative feature into the existing classifier*, never a
standalone regime label.

TRAIN/SERVE CONSISTENCY (the whole point)
-----------------------------------------
GKG 15-min files are a continuously-updated rolling archive: a file from
2020 and one from 15 minutes ago share an identical schema. The historical
backfill and the daily live tail therefore run the SAME code with the SAME
tight filter — zero train/serve skew. The only correct real-time source for
this feature is GDELT itself; substituting RSS / the DOC API live would feed
the classifier a differently-computed feature than it was trained on.

POINT-IN-TIME
-------------
A feature row is keyed by the calendar day it is *valid for a decision*,
which is `news_day + 1`. At the 09:00 IST premarket cron on day D, the whole
of D-1's news is known; D's own news is not. Keying by news_day+1 means
`read_macro_window(..., end=decision_date)` naturally returns yesterday's
complete aggregate and never leaks same-day/future news into a backtest.
Backfill and live use the SAME fixed intraday sampling cadence, so the
aggregate is reproducible identically offline and online.

FILTER (mandatory — the loose filter is ~80% noise)
----------------------------------------------------
Keep a GKG record only if: its source domain is in the Indian-financial-press
whitelist AND it is tagged India AND it carries a precise economic/EPU theme.

Series written to macro.duckdb `macro_daily` (no schema migration; it is a
tall (series_id, dt, value) table):
  gdelt_tone_mean      mean V2Tone of the kept set         (neg = risk-off)
  gdelt_tone_negfrac   fraction of kept records with tone<0
  gdelt_artcount       number of kept records (sampled)
  gdelt_epu_policy     1.0 if any EPU policy-uncertainty theme fired
  gdelt_centralbank    1.0 if any RBI/central-bank theme fired
  gdelt_tariff_trade   1.0 if any tariff/trade theme fired
  gdelt_inflation      1.0 if any inflation theme fired
"""
from __future__ import annotations

import csv
import io
import logging
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# GKG records carry very large fields (V2Themes / V2Locations / GCAM can be
# hundreds of KB). Python's csv default field cap is 128 KB, which aborts the
# WHOLE reader mid-file (not just one row). Raise it well past any GKG field.
csv.field_size_limit(10_000_000)

_GKG_BASE = "http://data.gdeltproject.org/gdeltv2/{stamp}.gkg.csv.zip"
_UA = {"User-Agent": "Mozilla/5.0 (autoresearch-trading-india gdelt ingest)"}

# Indian financial press — the domain whitelist that turns an 80%-noise feed
# into a usable signal (validated). Reuters/Bloomberg kept for India macro
# desks; broad domains deliberately excluded.
_FIN_DOMAINS = frozenset({
    "economictimes.indiatimes.com", "moneycontrol.com", "livemint.com",
    "business-standard.com", "thehindubusinessline.com", "ndtvprofit.com",
    "financialexpress.com", "cnbctv18.com", "businesstoday.in", "zeebiz.com",
    "goodreturns.in", "equitybulls.com", "reuters.com", "bloomberg.com",
    "thehindu.com", "indiatoday.in",
})

# Precise GKG V2 theme substrings → keep + flag. GDELT's EPU_* themes are the
# Economic-Policy-Uncertainty index inputs — purpose-built for regime work.
_THEME_KEEP = (
    "ECON_STOCKMARKET", "ECON_INTEREST_RATE", "ECON_CENTRALBANK",
    "ECON_INFLATION", "ECON_BUBBLE", "ECON_TAXATION", "ECON_TRADE",
    "ECON_FREETRADE", "ECON_SUBSIDIES", "ECON_CURRENCY",
    "ECON_EARNINGSREPORT", "ECON_RECESSION", "EPU_POLICY", "EPU_ECONOMY",
    "EPU_CATS",
)
_FLAG_THEMES = {
    "gdelt_epu_policy": ("EPU_POLICY", "EPU_ECONOMY", "EPU_CATS"),
    "gdelt_centralbank": ("ECON_CENTRALBANK", "ECON_INTEREST_RATE"),
    "gdelt_tariff_trade": ("ECON_TRADE", "ECON_FREETRADE", "ECON_SUBSIDIES"),
    "gdelt_inflation": ("ECON_INFLATION", "ECON_CURRENCY"),
}

_SERIES = (
    "gdelt_tone_mean", "gdelt_tone_negfrac", "gdelt_artcount",
    *(_FLAG_THEMES.keys()),
)

# Fixed sampling cadence (UTC) — used IDENTICALLY in backfill and live so the
# aggregate is reproducible. India news flow concentrates 02:00–12:00 UTC
# (07:30–17:30 IST); 6 evenly-spaced 15-min slices capture the daily tone
# without downloading all 96 files/day.
_DEFAULT_SLICE_HOURS = (2, 4, 6, 8, 10, 12)


def _stamps_for(day: date, slice_hours=_DEFAULT_SLICE_HOURS) -> list[str]:
    return [
        f"{day.strftime('%Y%m%d')}{h:02d}3000" for h in slice_hours
    ]


def _is_india(locations: str) -> bool:
    lo = locations.lower()
    return "india" in lo or ";IN;" in locations or "#IN#" in locations


def fetch_gkg_records(stamp: str, *, timeout: int = 60) -> list[tuple[str, float]] | None:
    """Return [(themes, tone)] of kept India-fin-econ records for one 15-min
    GKG file, or None if the file is missing (404 / not yet published)."""
    url = _GKG_BASE.format(stamp=stamp)
    try:
        r = requests.get(url, headers=_UA, timeout=timeout)
    except requests.RequestException as e:
        logger.warning("GKG fetch error %s: %s", stamp, e)
        return None
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        logger.warning("GKG %s HTTP %s", stamp, r.status_code)
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        raw = z.read(z.namelist()[0]).decode("utf-8", "replace")
        return _parse_gkg(raw)
    except Exception as e:
        # A single pathological file must never kill a multi-hour backfill —
        # it propagates through ThreadPoolExecutor.map otherwise. Degrade to
        # "no records for this slice".
        logger.warning("GKG %s parse failed (%s) — slice skipped", stamp, e)
        return None


def _parse_gkg(raw: str) -> list[tuple[str, float]]:
    """Parse a GKG 2.1 TSV body → kept (themes, tone) tuples.

    Columns (0-indexed): 3=SourceCommonName(domain) 4=DocumentIdentifier
    7=V2EnhancedThemes 9=V2Locations 15=V2Tone (csv; field 0 = tone).
    """
    out: list[tuple[str, float]] = []
    for row in csv.reader(io.StringIO(raw), delimiter="\t"):
        if len(row) < 16:
            continue
        domain = row[3].lower().strip()
        if domain not in _FIN_DOMAINS:
            continue
        themes = row[7]
        if not any(t in themes for t in _THEME_KEEP):
            continue
        if not _is_india(row[9]):
            continue
        try:
            tone = float(row[15].split(",")[0])
        except (ValueError, IndexError):
            continue
        out.append((themes, tone))
    return out


def compute_day_features(
    news_day: date, *, slice_hours=_DEFAULT_SLICE_HOURS,
    polite_delay_sec: float = 0.3,
) -> dict[str, float] | None:
    """Aggregate the kept GKG records across `news_day`'s sampled slices.

    Returns the feature dict, or None if no file for the day was reachable
    (vs. an empty dict-of-zeros when files exist but had no kept records —
    a real 'quiet news day' signal, distinct from missing data)."""
    stamps = _stamps_for(news_day, slice_hours)
    # The 6 slice files are independent network fetches — pull them
    # concurrently. GDELT's static bulk-download server tolerates modest
    # parallelism (it is designed for it); we cap at the slice count.
    with ThreadPoolExecutor(max_workers=len(stamps)) as ex:
        results = list(ex.map(fetch_gkg_records, stamps))
    recs: list[tuple[str, float]] = []
    any_file = False
    for got in results:
        if got is not None:
            any_file = True
            recs.extend(got)
    time.sleep(polite_delay_sec)  # small inter-day breather
    if not any_file:
        return None
    n = len(recs)
    feats: dict[str, float] = {
        "gdelt_artcount": float(n),
        "gdelt_tone_mean": round(sum(t for _, t in recs) / n, 4) if n else 0.0,
        "gdelt_tone_negfrac": (
            round(sum(1 for _, t in recs if t < 0) / n, 4) if n else 0.0
        ),
    }
    blob = " ".join(th for th, _ in recs)
    for flag, needles in _FLAG_THEMES.items():
        feats[flag] = 1.0 if any(nd in blob for nd in needles) else 0.0
    return feats


def ingest_gdelt(
    macro_db: Path,
    start: date,
    end: date,
    *,
    slice_hours=_DEFAULT_SLICE_HOURS,
    skip_existing: bool = True,
) -> dict[str, int]:
    """Backfill/refresh GDELT features for news-days in [start, end].

    Each news_day D's aggregate is written keyed at dt = D + 1 (the decision
    date it becomes valid for — see module docstring on point-in-time).
    Idempotent: re-running skips news-days already present unless
    skip_existing=False.
    """
    from data.ingest_macro import read_macro_window, write_macro_series

    written = 0
    days_done = 0
    missing = 0
    d = start
    while d <= end:
        valid_dt = d + timedelta(days=1)
        if skip_existing and read_macro_window(
            macro_db, "gdelt_tone_mean", valid_dt, valid_dt
        ):
            d += timedelta(days=1)
            continue
        feats = compute_day_features(d, slice_hours=slice_hours)
        if feats is None:
            missing += 1
            logger.info("GDELT %s: no file reachable, skipped", d)
            d += timedelta(days=1)
            continue
        for series_id, value in feats.items():
            written += write_macro_series(
                macro_db, series_id, [(valid_dt, value)]
            )
        days_done += 1
        if days_done % 20 == 0:
            logger.info(
                "GDELT progress: %s, %d days, %d rows, %d missing",
                d, days_done, written, missing,
            )
        d += timedelta(days=1)
    logger.info(
        "GDELT done %s..%s: %d days, %d rows, %d days missing",
        start, end, days_done, written, missing,
    )
    return {"days": days_done, "rows": written, "missing": missing}


def main(argv: list[str] | None = None) -> int:
    import argparse

    from data.ingest_macro import DB_PATH

    p = argparse.ArgumentParser(description=__doc__)
    today = date.today()
    p.add_argument("--start", type=date.fromisoformat,
                   default=today - timedelta(days=5 * 365))
    p.add_argument("--end", type=date.fromisoformat,
                   default=today - timedelta(days=1),
                   help="Inclusive last NEWS day (default: yesterday).")
    p.add_argument("--no-skip-existing", action="store_true",
                   help="Recompute days already in the DB.")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    res = ingest_gdelt(
        DB_PATH, args.start, args.end,
        skip_existing=not args.no_skip_existing,
    )
    print(f"GDELT ingest: {res}")
    return 0


__all__ = [
    "fetch_gkg_records",
    "compute_day_features",
    "ingest_gdelt",
    "_parse_gkg",
    "_stamps_for",
]


if __name__ == "__main__":
    raise SystemExit(main())
