"""Corporate-action ledger — minimal JSON-backed store.

Why a JSON file and not a duckdb table:
- CA list grows by ~0-3 rows per held name per quarter (tiny).
- Easy to inspect (`cat storage/corporate_actions.json`), easy to back up.
- No schema migration if we add fields later.

If we ever outgrow it (e.g., universe-wide CA history for backtest replay),
promote to a duckdb table — the loader/saver API stays the same shape.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CA_PATH = REPO_ROOT / "storage" / "corporate_actions.json"

# Action types we care about. `dividend` and `split` come from yfinance for
# free; the rest require manual entry (NSE bulletins) until we hook a
# real CA feed. Bonus is structurally a split; we keep the labels distinct
# so the journal records the intent ("BONUS 1:1" reads differently from
# "SPLIT 1:2" even though qty math is identical).
ALLOWED_TYPES = {
    "dividend",
    "split",
    "bonus",
    "demerger",
    "isin_change",
    "delisting",
    "suspension",
    "rights",
}


@dataclass(frozen=True)
class CorporateAction:
    """One CA event affecting one ticker.

    `value` is:
      - dividend → ₹/share (float)
      - split    → ratio target (e.g. 2.0 means "1 share becomes 2")
      - bonus    → ratio target (e.g. 2.0 means "1 share becomes 2", same as split)
      - rights   → ₹/share entitlement price
      - isin_change / delisting / suspension → None (use `new_symbol` for renames)
    """
    ex_date: date
    ticker: str
    type: str
    value: float | None = None
    new_symbol: str | None = None
    notes: str | None = None


def load_corporate_actions(
    path: Path | str | None = None,
) -> list[CorporateAction]:
    """Read the CA ledger. Returns [] if the file does not exist.

    `path=None` resolves to the module-level `DEFAULT_CA_PATH` at call
    time (NOT at function definition time), so tests can monkeypatch
    `DEFAULT_CA_PATH` and have it take effect.
    """
    p = Path(path) if path is not None else DEFAULT_CA_PATH
    if not p.exists():
        return []
    raw = json.loads(p.read_text())
    out: list[CorporateAction] = []
    for r in raw:
        out.append(
            CorporateAction(
                ex_date=date.fromisoformat(r["ex_date"]),
                ticker=r["ticker"],
                type=r["type"],
                value=(float(r["value"]) if r.get("value") is not None else None),
                new_symbol=r.get("new_symbol"),
                notes=r.get("notes"),
            )
        )
    return out


def save_corporate_actions(
    actions: list[CorporateAction], path: Path | str | None = None,
) -> None:
    """Write the CA ledger. Creates parent directory if needed.

    Idempotent w.r.t. content — re-saving the same list yields the same file.
    `path=None` resolves to module-level `DEFAULT_CA_PATH` at call time.
    """
    p = Path(path) if path is not None else DEFAULT_CA_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    serialized = [
        {
            "ex_date": ca.ex_date.isoformat(),
            "ticker": ca.ticker,
            "type": ca.type,
            "value": ca.value,
            "new_symbol": ca.new_symbol,
            "notes": ca.notes,
        }
        for ca in actions
    ]
    p.write_text(json.dumps(serialized, indent=2) + "\n")


def get_actions_on_date(
    actions: list[CorporateAction], d: date,
) -> list[CorporateAction]:
    return [ca for ca in actions if ca.ex_date == d]


def get_actions_for_tickers_on_date(
    actions: list[CorporateAction], tickers: set[str], d: date,
) -> list[CorporateAction]:
    """CAs intersecting both the date and a set of relevant tickers."""
    return [ca for ca in actions if ca.ex_date == d and ca.ticker in tickers]


def upsert_action(
    existing: list[CorporateAction], action: CorporateAction,
) -> tuple[list[CorporateAction], bool]:
    """Add `action` to `existing` if no row with the same (ticker, ex_date,
    type) key already exists. Returns (new_list, was_added)."""
    key = (action.ticker, action.ex_date, action.type)
    for ca in existing:
        if (ca.ticker, ca.ex_date, ca.type) == key:
            return existing, False
    return existing + [action], True


def format_action_summary(ca: CorporateAction) -> str:
    """Short human-readable summary for dashboard / journal."""
    if ca.type == "dividend":
        return f"{ca.ticker}: ₹{ca.value:.2f}/share dividend"
    if ca.type == "split":
        return f"{ca.ticker}: split → {ca.value:g}× shares"
    if ca.type == "bonus":
        return f"{ca.ticker}: bonus → {ca.value:g}× shares"
    if ca.type == "rights":
        return f"{ca.ticker}: rights issue @ ₹{ca.value:.2f}"
    if ca.type == "isin_change":
        return f"{ca.ticker} → {ca.new_symbol or '?'}: ISIN change"
    if ca.type == "delisting":
        return f"{ca.ticker}: delisted"
    if ca.type == "suspension":
        return f"{ca.ticker}: trading suspended"
    if ca.type == "demerger":
        return f"{ca.ticker}: demerger"
    return f"{ca.ticker}: {ca.type}"
