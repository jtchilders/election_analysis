"""
Canonical schemas and standard column definitions for election results across all years.
Ensures datasets produced in 2022, 2024, 2026, 2028+ share an identical interface,
enabling year-agnostic analysis and plotting scripts.
"""

from typing import Any
import pandas as pd

# Standard County-Level Schema (e.g. Presidential, Senate, Gubernatorial)
COUNTY_COLUMNS = [
    "Year",
    "Office",
    "State",
    "County",
    "Percent Reporting",
    "Total Votes",
    "Dem Candidate",
    "Dem Votes",
    "Dem Pct",
    "GOP Candidate",
    "GOP Votes",
    "GOP Pct",
    "Other Votes",
    "Other Pct",
    "Winner",
    "Winner Party",
    "Updated",
]

# Standard District / Candidate-Level Schema (e.g. House of Representatives)
DISTRICT_COLUMNS = [
    "Year",
    "Office",
    "State",
    "District",
    "Candidate",
    "Party",
    "Percentage of Votes (%)",
    "Total Votes",
    "Incumbent",
    "Percent Reporting",
    "Winner",
    "Updated",
]

# Statewide Race Summary Schema (e.g. Senate or Governor race overview)
STATE_SUMMARY_COLUMNS = [
    "Year",
    "Office",
    "State",
    "Percent Reporting",
    "Dem Candidate",
    "Dem Votes",
    "Dem Pct",
    "GOP Candidate",
    "GOP Votes",
    "GOP Pct",
    "Other Votes",
    "Other Pct",
    "Winner",
    "Winner Party",
    "Updated",
]


def standardize_party(party_raw: Any) -> str:
    """Normalize messy party strings into standard canonical names."""
    if party_raw is None or pd.isna(party_raw):
        return "Other"
    
    p = str(party_raw).strip().lower()
    if p in ["gop", "rep", "republican", "r"]:
        return "Republican"
    if p in ["dem", "democrat", "democratic", "d"]:
        return "Democrat"
    if p in ["lib", "libertarian", "l"]:
        return "Libertarian"
    if p in ["grn", "green", "g"]:
        return "Green"
    if p in ["ind", "independent", "i", "una", "unaffiliated"]:
        return "Independent"
    return "Other"


def clean_percentage(val: Any) -> float:
    """Safely convert strings or numbers to float percentage (0-100)."""
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).replace("%", "").replace("<", "").replace(">", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def clean_int(val: Any) -> int:
    """Safely convert vote counts or integers to int."""
    if val is None or pd.isna(val):
        return 0
    val_str = str(val).replace(",", "").strip()
    try:
        return int(float(val_str))
    except ValueError:
        return 0
