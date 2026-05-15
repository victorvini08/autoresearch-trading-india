"""Low-signal regulatory-filing filter for BSE / NSE corporate announcements.

BSE's announcement feed (our primary 5-year per-ticker history) is ~75%
mandatory procedural compliance: newspaper-publication notices, postal-ballot
scrutinizer reports, trading-window closures, SAST 29/31 shareholding
disclosures, BRSR/annual-report submissions, ESOP allotments, loss-of-
certificate notices, etc. None of these move a swing-trading position; they
just inflate the (ticker, date) cell count that the LLM sentiment/events
classifiers must process, which is the dominant precompute cost.

This module is a *pure predicate* — no I/O. `is_low_signal()` decides whether
a single (source, title, summary) row is procedural noise. It is applied at
the news *read* boundary (`data.ingest_news.read_news` / `count_news`), so:

  - raw rows are never deleted — the DuckDB table keeps everything;
  - the LLM precompute and the strategy's `news_volume()` accessor see only
    tradeable-signal articles, so a day with *only* procedural filings
    short-circuits as an empty-news cell (no LLM call);
  - raw access remains available via `include_low_signal=True`.

Only `source in {'bse', 'nse_filing'}` rows are ever filtered. RSS / macro /
RBI / SEBI press rows pass through untouched (they have no procedural-filing
taxonomy and are already high-signal).

Conservative by construction: an unrecognized announcement category is KEPT.
We only drop categories we have explicitly classified as non-tradeable.
"""
from __future__ import annotations

import re

_FILTERED_SOURCES = {"bse", "nse_filing"}

# Reg 30 (LODR) "Announcement under Regulation 30 (LODR)-<SUBTYPE>" carries its
# real category in the suffix after the ")-" / ") -" separator. We drop only
# the explicitly procedural subtypes; everything else (Press Release, Credit
# Rating, Acquisition, Order win, Earnings Call, board/exec changes, fund
# raising, dividend, scheme of arrangement, ...) is tradeable signal and kept.
_REG30_NOISE_SUFFIXES = {
    "newspaper publication",
    "analyst / investor meet - intimation",
    "allotment of esop / esps",
    "investor presentation",
    "allotment",
    "code of conduct under sebi (pit) regulations, 2015",
    "appointment of statutory auditor/s",
    "monitoring agency report",
    "amendments to memorandum & articles of association",
    "resignation of company secretary / compliance officer",
    "change in rta",
    "change in registered office address",
    "trading plan under sebi (pit) regulations, 2015",
    "forfeiture/cancellation",
    "regulation 57 (1)",  # interest/redemption payment certificate
    "general updates",
    "general announcement",
    "meeting updates",        # board/committee meeting scheduling
    "interest rates updates",
    "date of payment of dividend",
    "price movement",         # exchange-prompted "no info" clarification
    "amalgamation/ merger",   # the substantive update comes via "Acquisition"
    "appointment of cost auditor",
    "appointment of secretarial auditor",
}

# Non-Reg30 announcements: classified by normalized title prefix/keyword.
# Each pattern matches the lowercased, whitespace-collapsed title.
_NOISE_TITLE_PATTERNS = [
    # -- compliance certificates / RTA / reconciliation --
    r"^compliances?\b",                               # "Compliances-Reg. NN ..."
    r"^certificate under reg(ulation)? ?(7|40|74)\b",
    r"\bregulation ?40 ?\(?(9|10)\)?",
    r"^submission of compliance certificate",
    r"\bcompliance certificate under reg",
    r"^intimation under reg(ulation)? ?(57|7)\b",
    r"^reconciliation of share capital",
    r"^reg(ulation)? ?34 ?\(?1?\)?\b",               # annual report u/Reg 34
    r"^intimation under reg(ulation)? ?34\b",
    r"\bannual report\b",
    r"business responsibility and sustainability",    # BRSR
    # -- shareholding / pledge / SAST 29-31 --
    r"^disclosures? under reg(ulation)? ?(29|31)\b",
    r"\bsast\b",
    r"\b(pledge|encumbrance|invocation of pledge)\b",
    r"^disclosure under sebi.*substantial acquisition",
    # -- postal ballot / voting / scrutinizer --
    r"^shareholder meeting.*postal ballot",
    r"\bpostal ballot\b",
    r"^(disclosure of )?voting results\b",
    r"^scrutinizer'?s? report",
    # -- AGM / EGM scheduling (the *outcome*/results are kept separately) --
    r"\bannual general meeting\b",
    r"\bextra[- ]?ordinary general meeting\b",
    r"\begm\b",
    r"^notice (of|convening)\b",
    r"^proceedings of\b.*\bgeneral meeting",
    # -- board-meeting *intimation* (scheduling); outcomes are kept --
    r"^board meeting intimation\b",
    r"^board meeting - intimation",
    r"^intimation of board meeting",
    r"^corporate action[- ]board to consider",
    r"^update on board meeting",
    # -- trading window / insider-trading housekeeping --
    r"^closure of trading window",
    r"^trading window",
    r"^updates? on (newspaper|trading window)",
    r"\bcode of conduct\b",
    # -- newspaper / grievance / complaint housekeeping --
    r"^newspaper (publication|advertisement|clipping)",
    r"^(statement of )?investor complaint",
    r"^grievance redressal",
    r"^format of.*\binitial disclosure",
    r"^disclosure of related party transaction",
    # -- shareholder-servicing housekeeping (TDS / PAN-KYC / ESOP grants) --
    r"\b(deduction of tax|tax deduction|tds)\b",
    r"^reminder\b",
    r"\bphysical (securities|shares|share certificates|folio)\b",
    r"\b(pan|kyc)\b.*\b(furnish|nomination|update|detail)",
    r"^e-?mail communication to (members|shareholders)",
    r"^(submission of )?audio recording",            # transcript kept separately
    r"^audio-?visual recording",
    r"^(intimation of )?grant of (stock )?options?\b",
    r"\bunclaimed (dividend|shares)\b",
    r"\biepf\b",                                      # investor edu & protection fund
    r"^transfer of (shares|equity shares) to iepf",
    # -- bare record-date / book-closure procedural notices --
    r"^record date\b",
    r"^book closure\b",
    r"^fixation of record date",
]

_NOISE_TITLE_RE = re.compile("|".join(_NOISE_TITLE_PATTERNS))
_REG30_PREFIX_RE = re.compile(r"^announcement under regulation 30")
_REG30_SPLIT_RE = re.compile(r"\)\s*[-–]\s*")
_WS_RE = re.compile(r"\s+")

# A generic "Disclosure/Intimation under Regulation 30 of SEBI (LODR), 2015"
# with no informative subject is a pure wrapper. We detect it by removing all
# regulation-citation stopword tokens and checking whether any substantive
# word survives. Stopword-based (not a brittle regex) so both the "SEBI" and
# spelled-out "Securities and Exchange Board of India" variants collapse.
_GENERIC_REG_WRAPPER_RE = re.compile(
    r"^(disclosure|intimation|announcement) under regulation 30\b"
)
_REG_STOPWORDS = frozenset(
    """disclosure intimation announcement under of the and read with regulation
    regulations reg sub clause para a b c part schedule iii ii sebi securities
    exchange board india listing obligations requirement requirements lodr act
    1956 2011 2013 2014 2015 2018 2021 to as amended thereunder pursuant
    provisions applicable rules dated company limited ltd""".split()
)


def _norm(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip().lower())


def is_low_signal(source: str, title: str, summary: str = "") -> bool:
    """True if this corporate-filing row is procedural noise (drop it).

    Only `bse` / `nse_filing` rows are ever judged; any other source → False
    (kept). Unrecognized categories → False (kept) — we never drop on
    uncertainty.
    """
    if source not in _FILTERED_SOURCES:
        return False

    t = _norm(title)
    if not t:
        return False

    if _REG30_PREFIX_RE.match(t):
        parts = _REG30_SPLIT_RE.split(t, maxsplit=1)
        suffix = parts[1].strip() if len(parts) > 1 else ""
        if suffix == "":
            return True  # generic Reg30 wrapper with no subtype = boilerplate
        return suffix in _REG30_NOISE_SUFFIXES

    if _NOISE_TITLE_RE.search(t):
        return True

    # Bare "Disclosure/Intimation under Regulation 30 of SEBI (LODR), 2015"
    # with no real subject: drop the regulation-citation stopwords and see if
    # any substantive word survives.
    if _GENERIC_REG_WRAPPER_RE.match(t) and " - " not in t and ")-" not in t:
        words = re.findall(r"[a-z]{2,}", t)
        substantive = [w for w in words if w not in _REG_STOPWORDS]
        if not substantive:
            return True

    return False


__all__ = ["is_low_signal"]
