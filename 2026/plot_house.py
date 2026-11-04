"""
Analysis and visualization for 2026 US House midterm elections.
Consumes canonical schemas from common.schemas and generates:
1. Seats won / leading by party towards 218 majority.
2. Popular vote totals nationwide by party.
3. Vote efficiency (votes per representative won).
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.schemas import standardize_party
from common.plots import plot_party_seats, PARTY_COLORS

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

HOUSE_MAJORITY = 218


def plot_all_house_analytics(
    house_csv: str = "2026/US_House_results.csv",
    seats_fig: str = "2026/house_seats_by_party.png",
    votes_fig: str = "2026/house_votes_by_party.png",
    efficiency_fig: str = "2026/house_votes_per_representative.png",
):
    if not os.path.exists(house_csv):
        print(f"{house_csv} not found.")
        return

    df = pd.read_csv(house_csv)
    if df.empty:
        return

    df["Percentage of Votes (%)"] = pd.to_numeric(df["Percentage of Votes (%)"], errors="coerce").fillna(0)
    df["Total Votes"] = pd.to_numeric(df["Total Votes"], errors="coerce").fillna(0)
    df["Clean Party"] = df["Party"].apply(standardize_party)

    # 1. Seats plot
    plot_party_seats(df, majority_threshold=HOUSE_MAJORITY, out_fig=seats_fig)

    # 2. Popular votes by party
    total_votes = df.groupby("Clean Party")["Total Votes"].sum().reset_index()
    total_votes = total_votes[total_votes["Total Votes"] > 0]

    if not total_votes.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = [PARTY_COLORS[p]["called"] if p in PARTY_COLORS else "#718096" for p in total_votes["Clean Party"]]
        bars = ax.bar(total_votes["Clean Party"], total_votes["Total Votes"], color=colors, width=0.5)

        ax.set_ylabel("Total Popular Votes Cast", fontsize=11)
        ax.set_title("2026 Total U.S. House Votes Cast by Party", fontsize=13, fontweight="bold")

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval * 1.01, f"{int(yval):,}", ha="center", va="bottom", fontweight="bold")

        plt.savefig(votes_fig, dpi=200, bbox_inches="tight")
        print(f"Saved House Votes plot to {votes_fig}")
        plt.close()

        # 3. Votes per Representative (Efficiency)
        # Find winners/leaders
        winners = []
        for (state, dist), group in df.groupby(["State", "District"]):
            has_win = group[group["Winner"] == True]
            if not has_win.empty:
                winners.append(has_win.iloc[0])
            else:
                leading = group.loc[group["Percentage of Votes (%)"].idxmax()] if group["Percentage of Votes (%)"].max() > 0 else group.iloc[0]
                winners.append(leading)

        df_winners = pd.DataFrame(winners)
        seats_by_party = df_winners.groupby("Clean Party").size().reset_index(name="Seats")

        party_stats = pd.merge(seats_by_party, total_votes, on="Clean Party")
        party_stats = party_stats[party_stats["Seats"] > 0]
        party_stats["Votes per Seat"] = party_stats["Total Votes"] / party_stats["Seats"]

        fig, ax = plt.subplots(figsize=(8, 6))
        eff_colors = [PARTY_COLORS[p]["called"] if p in PARTY_COLORS else "#718096" for p in party_stats["Clean Party"]]
        bars = ax.bar(party_stats["Clean Party"], party_stats["Votes per Seat"], color=eff_colors, width=0.5)

        ax.set_ylabel("Votes Cast per Seat Won", fontsize=11)
        ax.set_title("2026 Vote Efficiency: Votes per House Seat Won", fontsize=13, fontweight="bold")

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval * 1.01, f"{int(yval):,}", ha="center", va="bottom", fontweight="bold")

        plt.savefig(efficiency_fig, dpi=200, bbox_inches="tight")
        print(f"Saved Vote Efficiency plot to {efficiency_fig}")
        plt.close()


if __name__ == "__main__":
    plot_all_house_analytics()
