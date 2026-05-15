"""GDELT GKG parser / feature-aggregation tests (no network)."""
from datetime import date
from pathlib import Path

from data.ingest_gdelt import _parse_gkg, _stamps_for, compute_day_features


def _row(domain, themes, locations, tone):
    """Build a 16+ col GKG TSV line. Cols: 3=domain 7=themes 9=loc 15=tone."""
    cols = [""] * 16
    cols[3] = domain
    cols[4] = "https://x/y"
    cols[7] = themes
    cols[9] = locations
    cols[15] = f"{tone},1,1,2,0,0,40"
    return "\t".join(cols)


def test_parse_keeps_only_india_fin_econ_rows():
    body = "\n".join([
        _row("moneycontrol.com", "ECON_CENTRALBANK;TAX_FNCACT",
             "1#India#IN#IN##20#78#IN", -3.5),                  # keep
        _row("livemint.com", "EPU_POLICY", "4#New Delhi, India", 1.2),  # keep
        _row("moneycontrol.com", "SPORTS;ENTERTAINMENT",
             "1#India#IN", 5.0),                                # drop: no econ theme
        _row("espn.com", "ECON_STOCKMARKET", "1#India#IN", -2.0),  # drop: domain
        _row("reuters.com", "ECON_INFLATION", "1#France#FR", 0.4),  # drop: not India
        "short\trow",                                            # drop: malformed
    ])
    recs = _parse_gkg(body)
    assert len(recs) == 2
    tones = sorted(t for _, t in recs)
    assert tones == [-3.5, 1.2]


def test_compute_day_features_aggregates(monkeypatch):
    fake = [
        ("ECON_CENTRALBANK", -2.0),
        ("EPU_POLICY", -1.0),
        ("ECON_STOCKMARKET", 3.0),
        ("ECON_TRADE;ECON_FREETRADE", 0.5),
    ]
    monkeypatch.setattr(
        "data.ingest_gdelt.fetch_gkg_records",
        lambda stamp, **kw: fake,
    )
    monkeypatch.setattr("data.ingest_gdelt.time.sleep", lambda *_: None)
    f = compute_day_features(date(2024, 6, 4))
    assert f is not None
    # 6 sampled slices × 4 recs = 24
    assert f["gdelt_artcount"] == 24.0
    assert abs(f["gdelt_tone_mean"] - 0.125) < 1e-6   # (-2-1+3+0.5)/4
    assert f["gdelt_tone_negfrac"] == 0.5             # 2 of 4 negative
    assert f["gdelt_epu_policy"] == 1.0
    assert f["gdelt_centralbank"] == 1.0
    assert f["gdelt_tariff_trade"] == 1.0
    assert f["gdelt_inflation"] == 0.0


def test_compute_day_features_none_when_no_files(monkeypatch):
    monkeypatch.setattr(
        "data.ingest_gdelt.fetch_gkg_records", lambda stamp, **kw: None
    )
    monkeypatch.setattr("data.ingest_gdelt.time.sleep", lambda *_: None)
    assert compute_day_features(date(2024, 6, 4)) is None


def test_stamps_use_fixed_utc_cadence():
    s = _stamps_for(date(2025, 2, 1))
    assert s == [
        "20250201023000", "20250201043000", "20250201063000",
        "20250201083000", "20250201103000", "20250201123000",
    ]


def test_ingest_writes_features_keyed_at_news_day_plus_one(tmp_path, monkeypatch):
    """Point-in-time: news day D → row valid at D+1, readable by the
    macro snapshot for a decision on D+1."""
    from data.ingest_gdelt import ingest_gdelt
    from llm.classify import _macro_snapshot

    monkeypatch.setattr(
        "data.ingest_gdelt.fetch_gkg_records",
        lambda stamp, **kw: [("EPU_POLICY;ECON_CENTRALBANK", -4.0)],
    )
    monkeypatch.setattr("data.ingest_gdelt.time.sleep", lambda *_: None)
    db = tmp_path / "macro.duckdb"
    res = ingest_gdelt(db, date(2024, 6, 3), date(2024, 6, 3))
    assert res["days"] == 1

    snap = _macro_snapshot(date(2024, 6, 4), macro_db=db)
    assert snap["gdelt_tone_mean"] == -4.0
    assert snap["gdelt_epu_policy"] == 1.0
    assert snap["gdelt_centralbank"] == 1.0
    # No leakage: a decision ON the news day must NOT see it.
    assert "gdelt_tone_mean" not in _macro_snapshot(date(2024, 6, 3), macro_db=db)
