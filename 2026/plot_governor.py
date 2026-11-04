"""
Analysis and visualization for 2026 US Governor midterm elections.
Consumes canonical schemas from common.schemas and utilizes shared plotting functions in common.plots.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.plots import (
    plot_balance_of_power,
    plot_statewide_margins,
    plot_turnout_projections,
    plot_cross_office_comparison,
)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

# Out of 50 total state governorships, 36 are up in 2026 and 14 are not up in 2026:
# Held Dem (6): DE, KY, NJ, NC, VA, WA
# Held GOP (8): IN, LA, MS, MO, MT, ND, UT, WV
HELD_DEM_GOVERNORS = 6
HELD_GOP_GOVERNORS = 8
MAJORITY_GOVERNORS = 26


if __name__ == "__main__":
    state_csv = "2026/US_Governor_state_results.csv"
    county_csv = "2026/US_Governor_county_results.csv"
    senate_state_csv = "2026/US_Senate_state_results.csv"

    if os.path.exists(state_csv):
        df_state = pd.read_csv(state_csv)
        plot_balance_of_power(
            df_state,
            office="Governor",
            held_dem=HELD_DEM_GOVERNORS,
            held_rep=HELD_GOP_GOVERNORS,
            majority_threshold=MAJORITY_GOVERNORS,
            out_fig="2026/governor_balance_of_power.png",
        )
        plot_statewide_margins(
            df_state,
            office="Governor",
            out_fig="2026/governor_battleground_margins.png",
        )

        if os.path.exists(senate_state_csv):
            df_senate = pd.read_csv(senate_state_csv)
            plot_cross_office_comparison(
                df_state,
                df_senate,
                office_primary="Governor",
                office_baseline="Senate",
                out_fig="2026/governor_vs_senate_ticket_splitting.png",
            )

    if os.path.exists(county_csv):
        df_county = pd.read_csv(county_csv)
        plot_turnout_projections(
            df_county,
            office="Governor",
            turnout_rate=0.60,
            out_fig="2026/governor_turnout_projection.png",
        )
