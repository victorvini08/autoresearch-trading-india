"""Unit tests for the BSE/NSE low-signal procedural-filing filter."""
import pytest

from data.news_filter import is_low_signal

# (title, expected_is_noise) for source='bse'
_NOISE = [
    "Announcement under Regulation 30 (LODR)-Newspaper Publication",
    "Announcement under Regulation 30 (LODR)-Allotment of ESOP / ESPS",
    "Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation",
    "Announcement under Regulation 30 (LODR)-Investor Presentation",
    "Announcement under Regulation 30 (LODR)-Allotment",
    "Compliances-Reg. 39 (3) - Details of Loss of Certificate / Duplicate Certificate",
    "Shareholder Meeting / Postal Ballot-Notice of Postal Ballot",
    "Shareholder Meeting / Postal Ballot-Scrutinizer's Report",
    "Disclosures under Reg. 29(1) of SEBI (SAST) Regulations, 2011",
    "Disclosures under Reg. 31(1) of SEBI (SAST) Regulations, 2011",
    "Closure of Trading Window",
    "Business Responsibility and Sustainability Reporting (BRSR)",
    "Reg. 34 (1) Annual Report",
    "Board Meeting Intimation for Consideration And Approval Of Financial Results",
    "Notice Convening The 38Th Annual General Meeting",
    "Intimation Regarding Annual General Meeting, Book Closure And Cut-Off Date",
    "Certificate Under Regulation 40 (9) Of SEBI (LODR) Regulations, 2015",
    "Compliance Certificate Under Regulation 7(3) Of SEBI (LODR)",
    "Reminder Letter To Holders Of Physical Securities For Furnishing Of PAN, KYC",
    "Disclosure Of Voting results of Postal Ballot (Regulation 44(3) of SEBI LODR)",
    "Intimation Under Regulation 30 Of The SEBI (Listing Obligations And "
    "Disclosure Requirements) Regulations, 2015",
    "Disclosure Under Regulation 30 Of SEBI (Listing Obligations And Disclosure "
    "Requirements). 2015.",
    "Audio Recording Of Conference Call",
    "Update on board meeting",
]

# Things that MUST survive the filter — tradeable signal.
_SIGNAL = [
    "Financial Results For The Quarter Ended 31 December 2021",
    "Board Meeting Outcome for Outcome Of Board Meeting Held On May 31, 2025",
    "Announcement under Regulation 30 (LODR)-Acquisition",
    "Announcement under Regulation 30 (LODR)-Credit Rating",
    "Announcement under Regulation 30 (LODR)-Press Release / Media Release",
    "Announcement under Regulation 30 (LODR)-Earnings Call Transcript",
    "Announcement under Regulation 30 (LODR)-Dividend Updates",
    "Announcement under Regulation 30 (LODR)-Change in Management",
    "POWERGRID Declared As Successful Bidder Under TBCB",
    "Ambuja Cements declared as the preferred bidder for the Devalmari Block",
    "Qualified Institutions Placement Of Equity Shares",
    "Imposition Of Monetary Penalty By The Reserve Bank Of India",
    "Composite Scheme Of Amalgamation For The Amalgamation Of HDFC",
    "Commissioning Of Cement Capacity",
    "Quarterly Disclosures Of Defaults On Payment Of Interest/Repayment Of Principal",
]


@pytest.mark.parametrize("title", _NOISE)
def test_procedural_filings_are_dropped(title):
    assert is_low_signal("bse", title, "") is True


@pytest.mark.parametrize("title", _SIGNAL)
def test_tradeable_filings_are_kept(title):
    assert is_low_signal("bse", title, "") is False


def test_non_filing_sources_pass_through():
    # RSS / macro / RBI / SEBI press are never judged, even if the title
    # superficially resembles a filing.
    for src in ("pulse_rss", "moneycontrol", "rbi", "sebi", "gdelt"):
        assert is_low_signal(src, "Closure of Trading Window", "") is False


def test_nse_filing_source_is_also_filtered():
    assert is_low_signal("nse_filing", "Closure of Trading Window", "") is True


def test_empty_title_is_kept():
    assert is_low_signal("bse", "", "some summary") is False
