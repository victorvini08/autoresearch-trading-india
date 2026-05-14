"""Parse-only tests for `data.ingest_fii_dii_history.parse_fii_dii_table`.

Verifies the scraper handles moneycontrol's layout robustly without
touching the network.
"""

from __future__ import annotations

from datetime import date

from data.ingest_fii_dii_history import parse_fii_dii_table


_SAMPLE_HTML = """\
<html><body><table>
  <thead><tr>
    <th>Date</th>
    <th>FII Gross Buy</th>
    <th>FII Gross Sell</th>
    <th>FII Net Buy/Sell</th>
    <th>DII Gross Buy</th>
    <th>DII Gross Sell</th>
    <th>DII Net Buy/Sell</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>14-May-2026</td>
      <td>10,500.00</td>
      <td>9,800.00</td>
      <td>700.00</td>
      <td>5,200.00</td>
      <td>4,000.00</td>
      <td>1,200.00</td>
    </tr>
    <tr>
      <td>13-May-2026</td>
      <td>11,200.00</td>
      <td>13,000.00</td>
      <td>-1,800.00</td>
      <td>5,500.00</td>
      <td>3,200.00</td>
      <td>2,300.00</td>
    </tr>
    <tr>
      <td>12-May-2026</td>
      <td>10,000.00</td>
      <td>10,500.00</td>
      <td>(500.00)</td>
      <td>4,800.00</td>
      <td>4,000.00</td>
      <td>800.00</td>
    </tr>
  </tbody>
</table></body></html>
"""


def test_parses_standard_layout() -> None:
    rows = parse_fii_dii_table(_SAMPLE_HTML)
    by_date = {r[0]: r for r in rows}
    assert date(2026, 5, 14) in by_date
    assert by_date[date(2026, 5, 14)] == (date(2026, 5, 14), 700.00, 1200.00)
    assert by_date[date(2026, 5, 13)] == (date(2026, 5, 13), -1800.00, 2300.00)
    # Accountancy-style negative (500.00) → -500.00
    assert by_date[date(2026, 5, 12)] == (date(2026, 5, 12), -500.00, 800.00)


def test_dedup_by_date() -> None:
    """If two table appearances on a page give the same date, keep one row."""
    html = _SAMPLE_HTML + "\n" + _SAMPLE_HTML  # same page twice
    rows = parse_fii_dii_table(html)
    dates_seen = [r[0] for r in rows]
    assert len(dates_seen) == len(set(dates_seen))


def test_empty_table_returns_empty() -> None:
    rows = parse_fii_dii_table("<html><body></body></html>")
    assert rows == []


def test_rows_sorted_ascending() -> None:
    rows = parse_fii_dii_table(_SAMPLE_HTML)
    dates = [r[0] for r in rows]
    assert dates == sorted(dates)
