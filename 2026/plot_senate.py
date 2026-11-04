"""
Analysis and visualization for 2026 US Senate midterm elections.
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
)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

# Out of 100 total U.S. Senate seats, 35 are up in 2026 and 65 are not up in 2026:
HELD_DEM_SENATE = 34
HELD_GOP_SENATE = 31
MAJORITY_SENATE = 50


if __name__ == "__main__":
    state_csv = "2026/US_Senate_state_results.csv"
    county_csv = "2026/US_Senate_county_results.csv"

    if os.path.exists(state_csv):
        df_state = pd.read_csv(state_csv)
        plot_balance_of_power(
            df_state,
            office="Senate",
            held_dem=HELD_DEM_SENATE,
            held_rep=HELD_GOP_SENATE,
            majority_threshold=MAJORITY_SENATE,
            out_fig="2026/senate_balance_of_power.png",
        )
        plot_statewide_margins(
            df_state,
            office="Senate",
            out_fig="2026/senate_battleground_margins.png",
        )

    if os.path.exists(county_csv):
        df_county = pd.read_csv(county_csv)
        plot_turnout_projections(
            df_county,
            office="Senate",
            turnout_rate=0.60,
            out_fig="2026/senate_turnout_projection.png",
        )
