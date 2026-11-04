"""
Common election analysis package.
Provides canonical schemas, polite HTTP fetching with caching, and reusable plotting utilities.
"""

from .schemas import (
    COUNTY_COLUMNS,
    DISTRICT_COLUMNS,
    STATE_SUMMARY_COLUMNS,
    standardize_party,
    clean_percentage,
    clean_int,
)
from .fetcher import PoliteFetcher
from .plots import (
    plot_balance_of_power,
    plot_statewide_margins,
    plot_party_seats,
    plot_turnout_projections,
    plot_cross_office_comparison,
    get_top_independent_pct_by_state,
)
