"""Unit tests for `brokers.dhan.DhanBroker` — REST client, mocked HTTP."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from brokers.dhan import (
    DhanBroker,
    OrderRequest,
    parse_scrip_master,
)


def _set_env(monkeypatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "fake_token")
    monkeypatch.setenv("DHAN_CLIENT_ID", "1000001234")
    monkeypatch.setenv("SEBI_ALGO_ID", "ALGO_TEST_001")


_SCRIP_MASTER_CSV = """\
SEM_EXM_EXCH_ID,SEM_SMST_SECURITY_ID,SEM_TRADING_SYMBOL,SEM_INSTRUMENT_NAME,SEM_LOT_UNITS,SEM_TICK_SIZE,ISIN
NSE,1234,RELIANCE,EQUITY,1,0.05,INE002A01018
NSE,5678,INFY,EQUITY,1,0.05,INE009A01021
BSE,9999,FOO,EQUITY,1,0.01,INE000Z01001
NSE,0,IDEA,SME,1,0.05,INE669E01016
"""


def test_parse_scrip_master_filters_nse_eq_only() -> None:
    mapping = parse_scrip_master(_SCRIP_MASTER_CSV)
    assert set(mapping.keys()) == {"RELIANCE", "INFY"}
    assert mapping["RELIANCE"]["SEM_SMST_SECURITY_ID"] == "1234"


def test_constructor_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("DHAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError):
        DhanBroker()


def test_place_order_stamps_sebi_algo_id(monkeypatch, tmp_path) -> None:
    _set_env(monkeypatch)
    cache = tmp_path / "scrip_master.csv"
    cache.write_text(_SCRIP_MASTER_CSV)

    with patch("brokers.dhan.requests.Session") as session_cls:
        session = MagicMock()
        session_cls.return_value = session
        # The POST /v2/orders call returns this
        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.text = '{"orderId": "MOCK-1", "orderStatus": "PENDING"}'
        post_resp.json.return_value = {"orderId": "MOCK-1", "orderStatus": "PENDING"}
        post_resp.raise_for_status.return_value = None
        session.request.return_value = post_resp

        b = DhanBroker(scrip_master_cache=cache)
        resp = b.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))

        # Inspect the call args to confirm the algo_id was included
        args, kwargs = session.request.call_args
        body = kwargs.get("json") or {}
        assert body["correlationId"] == "ALGO_TEST_001"
        assert body["dhanClientId"] == "1000001234"
        assert body["productType"] == "CNC"
        assert body["exchangeSegment"] == "NSE_EQ"
        assert body["securityId"] == "1234"
        assert resp.order_id == "MOCK-1"


def test_limit_order_requires_price(monkeypatch, tmp_path) -> None:
    _set_env(monkeypatch)
    cache = tmp_path / "scrip.csv"
    cache.write_text(_SCRIP_MASTER_CSV)
    with patch("brokers.dhan.requests.Session") as session_cls:
        session_cls.return_value = MagicMock()
        b = DhanBroker(scrip_master_cache=cache)
        with pytest.raises(ValueError):
            b.place_order(OrderRequest("BUY", "RELIANCE", 10, "LIMIT"))


def test_unknown_ticker_raises_keyerror(monkeypatch, tmp_path) -> None:
    _set_env(monkeypatch)
    cache = tmp_path / "scrip.csv"
    cache.write_text(_SCRIP_MASTER_CSV)
    with patch("brokers.dhan.requests.Session") as session_cls:
        session_cls.return_value = MagicMock()
        b = DhanBroker(scrip_master_cache=cache)
        with pytest.raises(KeyError):
            b.security_id_for("DOES_NOT_EXIST")
