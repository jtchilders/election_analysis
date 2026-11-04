"""
Year-agnostic plotting and projection utilities for election analysis.
These functions consume canonical schemas defined in common.schemas,
explicitly accounting for how much of the vote has been counted (Percent Reporting):
- Distinguishes officially called winners from leads.
- Distinguishes mature leads (>=50% reporting) from early leads (<50% reporting).
- Accounts for Independent/Other challengers leading major races (e.g., NE, ID).
- Extrapolates county-level turnout and projected final popular votes based on reporting rates.
- Compares statewide margins across offices on the same ballot (e.g., Governor vs. Senate/House).
"""

import os
import glob
import json
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from .schemas import standardize_party

# Standard party color palette
PARTY_COLORS = {
    "Democrat": {
        "called": "#1f4e79",      # Dark solid blue
        "lead_50": "#2b6cb0",     # Medium blue
        "lead_early": "#7fb3d5",  # Light blue
        "held": "#5b9bd5",        # Slate blue
    },
    "Republican": {
        "called": "#900c3f",      # Dark solid red
        "lead_50": "#c53030",     # Medium red
        "lead_early": "#f1948a",  # Light red
        "held": "#ed7d31",        # Amber / orange-red
    },
    "Independent / Other": {
        "called": "#553c9a",      # Dark purple
        "lead_50": "#805ad5",     # Medium purple
        "lead_early": "#b794f4",  # Light purple
        "held": "#9f7aea",
    },
    "Other": {
        "called": "#276749",
        "lead_50": "#38a169",
        "lead_early": "#9ae6b4",
        "held": "#718096",
    },
}


def get_top_independent_pct_by_state(office: str = "Senate", year: int = 2026) -> dict[str, tuple[str, float]]:
    """
    Read cached state JSONs (if available) to get the single top Independent/Third-party
    candidate's name and vote percentage (rather than the sum of all minor candidates).
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    office_slug = f"{office.lower()}-results"
    cache_pattern = os.path.join(repo_root, str(year), ".cache", f"*{office_slug}*.json")
    top_ind = {}
    for f in glob.glob(cache_pattern):
        if "national" in os.path.basename(f):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            st = d.get("stateName")
            cands = d.get("races", [{}])[0].get("summary", {}).get("candidates", [])
            ind_cands = [c for c in cands if (c.get("party") or "").lower() not in ["dem", "gop"]]
            if ind_cands:
                best = max(ind_cands, key=lambda c: float(c.get("percentVote", 0) or 0))
                top_ind[st] = (best.get("name", "Independent"), float(best.get("percentVote", 0) or 0))
        except Exception:
            pass
    return top_ind


def plot_balance_of_power(
    state_df: pd.DataFrame,
    office: str = "Senate",
    held_dem: int = 34,
    held_rep: int = 31,
    majority_threshold: int = 50,
    out_fig: Optional[str] = None,
):
    """
    Plot Balance of Power explicitly accounting for how much vote is counted:
    - Held baseline (seats not up in this cycle)
    - Officially called contests (networks declared winner)
    - Leading with >= 50% counted (mature leads)
    - Early leads with < 50% counted (early returns)
    - Independents / Other leading in states without a major-party Dem nominee
    """
    if state_df.empty:
        print("Cannot plot balance of power: state_df is empty.")
        return

    year = int(state_df["Year"].iloc[0]) if "Year" in state_df.columns and not state_df.empty else 2026
    top_ind_map = get_top_independent_pct_by_state(office=office, year=year)

    dem = {"called": 0, "lead_50": 0, "lead_early": 0}
    rep = {"called": 0, "lead_50": 0, "lead_early": 0}
    ind = {"called": 0, "lead_50": 0, "lead_early": 0}
    unreported = 0

    for _, row in state_df.iterrows():
        st_name = str(row.get("State", ""))
        pct = float(row.get("Percent Reporting", 0) or 0)
        winner_name = str(row.get("Winner", "") or "").strip()
        winner_party = str(row.get("Winner Party", "") or "").strip().capitalize()
        dem_pct = float(row.get("Dem Pct", 0) or 0)
        gop_pct = float(row.get("GOP Pct", 0) or 0)
        oth_pct = top_ind_map[st_name][1] if st_name in top_ind_map else float(row.get("Other Pct", 0) or 0)

        if winner_name and winner_name != "nan":
            if "Dem" in winner_party:
                dem["called"] += 1
            elif "Rep" in winner_party or "Gop" in winner_party:
                rep["called"] += 1
            else:
                ind["called"] += 1
        elif pct == 0:
            unreported += 1
        else:
            tier = "lead_50" if pct >= 50 else "lead_early"
            if dem_pct >= gop_pct and dem_pct >= oth_pct:
                dem[tier] += 1
            elif gop_pct >= dem_pct and gop_pct >= oth_pct:
                rep[tier] += 1
            else:
                ind[tier] += 1

    tot_dem_called = held_dem + dem["called"]
    tot_rep_called = held_rep + rep["called"]
    tot_ind_called = ind["called"]

    tot_dem_all = tot_dem_called + dem["lead_50"] + dem["lead_early"]
    tot_rep_all = tot_rep_called + rep["lead_50"] + rep["lead_early"]
    tot_ind_all = tot_ind_called + ind["lead_50"] + ind["lead_early"]

    print(f"\n=== Granular {office} Balance of Power ===")
    print(f"Democratic:  Held {held_dem} | Called {dem['called']} (Total Called: {tot_dem_called}) | Lead >=50%: {dem['lead_50']} | Lead <50%: {dem['lead_early']} | Total: {tot_dem_all}")
    print(f"Republican:  Held {held_rep} | Called {rep['called']} (Total Called: {tot_rep_called}) | Lead >=50%: {rep['lead_50']} | Lead <50%: {rep['lead_early']} | Total: {tot_rep_all}")
    if tot_ind_all > 0:
        print(f"Ind / Other: Held  0 | Called {ind['called']} (Total Called: {tot_ind_called}) | Lead >=50%: {ind['lead_50']} | Lead <50%: {ind['lead_early']} | Total: {tot_ind_all}")
    print(f"Unreported / 0% in: {unreported}")

    cats = ["Democrat", "Republican"]
    if tot_ind_all > 0:
        cats.append("Independent / Other")

    h_held = [held_dem, held_rep] + ([0] if tot_ind_all > 0 else [])
    h_called = [dem["called"], rep["called"]] + ([ind["called"]] if tot_ind_all > 0 else [])
    h_lead50 = [dem["lead_50"], rep["lead_50"]] + ([ind["lead_50"]] if tot_ind_all > 0 else [])
    h_early = [dem["lead_early"], rep["lead_early"]] + ([ind["lead_early"]] if tot_ind_all > 0 else [])

    n = len(cats)
    b_called = h_held
    b_lead50 = [h_held[i] + h_called[i] for i in range(n)]
    b_early = [b_lead50[i] + h_lead50[i] for i in range(n)]

    fig, ax = plt.subplots(figsize=(9.5, 6.5))

    ax.bar(cats, h_held, label=f"Not Up in {year} (Held Baseline)", color=[PARTY_COLORS[c]["held"] for c in cats], width=0.45)
    ax.bar(cats, h_called, bottom=b_called, label="Officially Called Wins", color=[PARTY_COLORS[c]["called"] for c in cats], width=0.45)
    ax.bar(cats, h_lead50, bottom=b_lead50, label="Leading with ≥50% Counted", color=[PARTY_COLORS[c]["lead_50"] for c in cats], width=0.45, hatch="//")
    ax.bar(cats, h_early, bottom=b_early, label="Early Lead (<50% Counted)", color=[PARTY_COLORS[c]["lead_early"] for c in cats], width=0.45, hatch="..")

    ax.axhline(majority_threshold, color="black", linestyle="--", linewidth=1.5, label=f"Majority Threshold ({majority_threshold})")
    ax.set_ylabel(f"Total {office} Seats / Governorships" if office == "Governor" else f"Total {office} Seats", fontsize=11)
    max_bar = max([b_early[i] + h_early[i] for i in range(n)] + [majority_threshold])
    ax.set_ylim(0, max(int(max_bar * 1.22), majority_threshold + 10))
    ax.set_title(f"{year} U.S. {office} Balance of Power: Called vs. Leading", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", framealpha=0.95)

    for i, cat in enumerate(cats):
        called_tot = h_held[i] + h_called[i]
        grand_tot = b_early[i] + h_early[i]
        if called_tot > 0:
            ax.text(i, called_tot / 2.0, f"Called: {called_tot}", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
        ax.text(i, grand_tot + (max_bar * 0.02), f"Total + Leads: {grand_tot}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    if out_fig:
        plt.savefig(out_fig, dpi=200, bbox_inches="tight")
        print(f"Saved Balance of Power plot to {out_fig}")
        plt.close()
    else:
        plt.show()


def plot_statewide_margins(
    state_df: pd.DataFrame,
    office: str = "Senate",
    out_fig: Optional[str] = None,
):
    """
    Plot vote margins across all reporting statewide contests (e.g. Senate or Governor).
    Compares the leading non-GOP challenger (Democrat or top single Independent) against the GOP nominee,
    properly highlighting states where Independent challengers lead or are the primary challenger.
    """
    if state_df.empty:
        print(f"Cannot plot {office} margins: state_df is empty.")
        return

    df = state_df.copy()
    year = int(df["Year"].iloc[0]) if "Year" in df.columns and not df.empty else 2026
    top_ind_map = get_top_independent_pct_by_state(office=office, year=year)

    for col in ["Dem Pct", "GOP Pct", "Other Pct", "Percent Reporting"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[df["Percent Reporting"] > 0].copy()
    if df.empty:
        print(f"No reporting states (>0% in) for {office}.")
        return

    df["Top_Ind_Pct"] = df["State"].map(lambda s: top_ind_map.get(s, ("", 0.0))[1])
    df["Top_Ind_Name"] = df["State"].map(lambda s: top_ind_map.get(s, ("", 0.0))[0])
    df["Top_Ind_Pct"] = np.where(df["Top_Ind_Pct"] > 0, df["Top_Ind_Pct"], df["Other Pct"])

    df["Challenger_Pct"] = np.maximum(df["Dem Pct"], df["Top_Ind_Pct"])
    df["Is_Ind_Challenger"] = df["Top_Ind_Pct"] > df["Dem Pct"]
    df["Margin (Challenger - GOP)"] = df["Challenger_Pct"] - df["GOP Pct"]

    df["State_Label"] = df.apply(
        lambda r: f"{r['State']} ({r['Top_Ind_Name'].split()[-1]} - Ind)"
        if r["Is_Ind_Challenger"] and r["Top_Ind_Name"]
        else (f"{r['State']} (Ind)" if r["Is_Ind_Challenger"] else str(r["State"])),
        axis=1,
    )

    df_sorted = df.sort_values(by="Margin (Challenger - GOP)", ascending=True)

    fig, ax = plt.subplots(figsize=(10.5, max(7.5, len(df_sorted) * 0.25)))
    colors = []
    for _, r in df_sorted.iterrows():
        m = r["Margin (Challenger - GOP)"]
        if m >= 0:
            colors.append("#805ad5" if r["Is_Ind_Challenger"] else "#2b6cb0")
        else:
            colors.append("#c53030")

    bars = ax.barh(df_sorted["State_Label"], df_sorted["Margin (Challenger - GOP)"], color=colors, height=0.72)

    ax.axvline(0, color="black", linestyle="-", linewidth=1.0)
    ax.set_xlabel("Margin (% Points: Positive = Dem/Ind Lead, Negative = GOP Lead)", fontsize=11)
    ax.set_title(f"{year} U.S. {office} Race Margins Across {len(df_sorted)} Reporting States", fontsize=13, fontweight="bold")
    min_m = min(-42.0, df_sorted["Margin (Challenger - GOP)"].min() - 8.0)
    max_m = max(45.0, df_sorted["Margin (Challenger - GOP)"].max() + 8.0)
    ax.set_xlim(min_m, max_m)

    for bar in bars:
        width = bar.get_width()
        offset = 0.6 if width >= 0 else -0.6
        ha = "left" if width >= 0 else "right"
        ax.text(width + offset, bar.get_y() + bar.get_height() / 2, f"{width:+.1f}%", va="center", ha=ha, fontsize=8.5, fontweight="bold")

    legend_elements = [
        Patch(facecolor="#2b6cb0", label="Democrat Leading / Won"),
        Patch(facecolor="#805ad5", label="Independent Challenger Leading"),
        Patch(facecolor="#c53030", label="Republican Leading / Won"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", framealpha=0.95)

    if out_fig:
        plt.savefig(out_fig, dpi=200, bbox_inches="tight")
        print(f"Saved {office} Margins plot to {out_fig}")
        plt.close()
    else:
        plt.show()


def plot_party_seats(
    district_df: pd.DataFrame,
    majority_threshold: int = 218,
    out_fig: Optional[str] = None,
):
    """
    Plot district-level seats explicitly accounting for vote reporting progress:
    - Stack 1: Officially Called Winners
    - Stack 2: Leading with >=50% counted
    - Stack 3: Early leads with <50% counted
    - Districts with 0% reporting are NOT credited to any party.
    """
    if district_df.empty:
        print("Cannot plot seats: district_df is empty.")
        return

    df = district_df.copy()
    df["Clean Party"] = df["Party"].apply(standardize_party)

    stats = {
        "Democrat": {"called": 0, "lead_50": 0, "lead_early": 0},
        "Republican": {"called": 0, "lead_50": 0, "lead_early": 0},
        "Other": {"called": 0, "lead_50": 0, "lead_early": 0},
    }
    unreported_count = 0

    for (state, dist), group in df.groupby(["State", "District"]):
        pct = float(group["Percent Reporting"].iloc[0] or 0)
        has_win = group[group["Winner"] == True]

        if not has_win.empty:
            p = has_win.iloc[0]["Clean Party"]
            if p in stats:
                stats[p]["called"] += 1
            continue

        if pct == 0:
            unreported_count += 1
            continue

        leading_cand = group.loc[group["Percentage of Votes (%)"].idxmax()] if group["Percentage of Votes (%)"].max() > 0 else None
        if leading_cand is not None:
            p = leading_cand["Clean Party"]
            if p in stats:
                if pct >= 50:
                    stats[p]["lead_50"] += 1
                else:
                    stats[p]["lead_early"] += 1
        else:
            unreported_count += 1

    cats = ["Democrat", "Republican"]
    called = [stats[c]["called"] for c in cats]
    lead50 = [stats[c]["lead_50"] for c in cats]
    early = [stats[c]["lead_early"] for c in cats]

    b_lead50 = called
    b_early = [called[i] + lead50[i] for i in range(len(cats))]

    print("\n=== Granular House Seats Breakdown ===")
    print(f"Democrat:   Called {called[0]} | Lead >=50%: {lead50[0]} | Early Lead (<50%): {early[0]} | Max Potential: {called[0]+lead50[0]+early[0]}")
    print(f"Republican: Called {called[1]} | Lead >=50%: {lead50[1]} | Early Lead (<50%): {early[1]} | Max Potential: {called[1]+lead50[1]+early[1]}")
    print(f"Unreported (0% reporting): {unreported_count}")

    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    ax.bar(cats, called, label="Officially Called Seats", color=[PARTY_COLORS[c]["called"] for c in cats], width=0.45)
    ax.bar(cats, lead50, bottom=b_lead50, label="Leading with ≥50% Counted", color=[PARTY_COLORS[c]["lead_50"] for c in cats], width=0.45, hatch="//")
    ax.bar(cats, early, bottom=b_early, label="Early Lead (<50% Counted)", color=[PARTY_COLORS[c]["lead_early"] for c in cats], width=0.45, hatch="..")

    if majority_threshold:
        ax.axhline(majority_threshold, color="black", linestyle="--", linewidth=1.5, label=f"Majority Threshold ({majority_threshold} seats)")

    ax.set_ylabel("Number of Congressional Seats", fontsize=11)
    ax.set_ylim(0, 300)
    ax.set_title("2026 U.S. House Seats: Called vs. Leading by Vote Progress", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", framealpha=0.95)

    for i, c in enumerate(cats):
        tot_called = called[i]
        tot_all = called[i] + lead50[i] + early[i]
        ax.text(i, tot_called / 2.0, f"Called: {tot_called}", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
        ax.text(i, tot_all + 3, f"Total + Leads: {tot_all}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    if out_fig:
        plt.savefig(out_fig, dpi=200, bbox_inches="tight")
        print(f"Saved Party Seats plot to {out_fig}")
        plt.close()
    else:
        plt.show()


def plot_turnout_projections(
    county_df: pd.DataFrame,
    office: str = "Senate",
    turnout_rate: float = 0.60,
    out_fig: Optional[str] = None,
):
    """
    Project total votes across all counties explicitly using 'Percent Reporting':
    County Projected Total = Current Counted Votes / (Percent Reporting / 100).
    Candidate Projected Votes = County Projected Total * (Candidate Pct / 100).
    """
    if county_df.empty:
        print("Cannot project turnout: county_df is empty.")
        return

    df = county_df.copy()
    if "Office" in df.columns and not df["Office"].dropna().empty:
        office = str(df["Office"].dropna().iloc[0])

    for col in ["Percent Reporting", "Dem Pct", "GOP Pct", "Other Pct", "Total Votes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    counted_counties = df[df["Percent Reporting"] > 0].copy()
    if counted_counties.empty:
        print("Note: All reporting percentages are currently zero. Turnout projection skipped.")
        return

    counted_counties["Estimated Total Votes"] = (
        counted_counties["Total Votes"] / (counted_counties["Percent Reporting"] / 100.0)
    )

    counted_counties["Projected Dem Votes"] = counted_counties["Estimated Total Votes"] * (counted_counties["Dem Pct"] / 100.0)
    counted_counties["Projected GOP Votes"] = counted_counties["Estimated Total Votes"] * (counted_counties["GOP Pct"] / 100.0)
    counted_counties["Projected Other Votes"] = counted_counties["Estimated Total Votes"] * (counted_counties["Other Pct"] / 100.0)

    actual_counted = counted_counties["Total Votes"].sum()
    tot_dem = counted_counties["Projected Dem Votes"].sum()
    tot_gop = counted_counties["Projected GOP Votes"].sum()
    tot_oth = counted_counties["Projected Other Votes"].sum()
    tot_proj = tot_dem + tot_gop + tot_oth

    avg_reporting = counted_counties["Percent Reporting"].mean()

    print(f"\n=== {office} Turnout Projections Based on Counted Votes ===")
    print(f"Counties reporting votes: {len(counted_counties)} / {len(df)}")
    print(f"Average reporting progress: {avg_reporting:.1f}%")
    print(f"Raw votes counted so far: {actual_counted:,}")
    print(f"Projected total votes at 100% in: {tot_proj:,.0f}")
    print(f"  - Projected Dem: {tot_dem:,.0f} ({(tot_dem/tot_proj)*100:.1f}%)")
    print(f"  - Projected GOP: {tot_gop:,.0f} ({(tot_gop/tot_proj)*100:.1f}%)")
    print(f"  - Projected Other/Ind: {tot_oth:,.0f} ({(tot_oth/tot_proj)*100:.1f}%)")

    fig, ax = plt.subplots(figsize=(8, 6))
    cands = ["Democratic", "Republican", "Independent / Other"]
    votes = [tot_dem, tot_gop, tot_oth]
    colors = [PARTY_COLORS["Democrat"]["called"], PARTY_COLORS["Republican"]["called"], PARTY_COLORS["Independent / Other"]["called"]]

    bars = ax.bar(cands, votes, color=colors, width=0.5)
    ax.set_ylabel("Projected Total Votes When 100% In", fontsize=11)
    ax.set_ylim(0, max(votes) * 1.15)
    ax.set_title(f"Projected {office} Popular Vote (Based on {avg_reporting:.0f}% Counted)", fontsize=13, fontweight="bold")

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, yval + (max(votes) * 0.015), f"{int(yval):,}\n({(yval/tot_proj)*100:.1f}%)", ha="center", va="bottom", fontweight="bold")

    if out_fig:
        plt.savefig(out_fig, dpi=200, bbox_inches="tight")
        print(f"Saved Turnout Projection plot to {out_fig}")
        plt.close()
    else:
        plt.show()


def plot_cross_office_comparison(
    df_primary: pd.DataFrame,
    df_baseline: pd.DataFrame,
    office_primary: str = "Governor",
    office_baseline: str = "Senate",
    out_fig: Optional[str] = None,
):
    """
    Compare statewide vote margins across two statewide offices on the same ballot
    (e.g., Governor vs. Senate) to reveal ticket-splitting and candidate overperformance.
    Both DataFrames follow STATE_SUMMARY_COLUMNS.
    """
    if df_primary.empty or df_baseline.empty:
        return

    p_df = df_primary[df_primary["Percent Reporting"] > 10].copy()
    b_df = df_baseline[df_baseline["Percent Reporting"] > 10].copy()
    if p_df.empty or b_df.empty:
        return

    year = int(p_df["Year"].iloc[0]) if "Year" in p_df.columns else 2026
    ind_p = get_top_independent_pct_by_state(office=office_primary, year=year)
    ind_b = get_top_independent_pct_by_state(office=office_baseline, year=year)

    p_df["Top_Ind_P"] = p_df["State"].map(lambda s: ind_p.get(s, ("", 0.0))[1])
    p_df["Challenger_P"] = np.maximum(p_df["Dem Pct"], p_df["Top_Ind_P"])
    p_df["Margin_Primary"] = p_df["Challenger_P"] - p_df["GOP Pct"]

    b_df["Top_Ind_B"] = b_df["State"].map(lambda s: ind_b.get(s, ("", 0.0))[1])
    b_df["Challenger_B"] = np.maximum(b_df["Dem Pct"], b_df["Top_Ind_B"])
    b_df["Margin_Baseline"] = b_df["Challenger_B"] - b_df["GOP Pct"]

    comp = pd.merge(
        p_df[["State", "Dem Candidate", "GOP Candidate", "Margin_Primary"]],
        b_df[["State", "Margin_Baseline"]],
        on="State",
        how="inner",
    )
    if comp.empty:
        return

    comp["Diff"] = comp["Margin_Primary"] - comp["Margin_Baseline"]
    comp = comp.sort_values("Diff", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, max(7.5, len(comp) * 0.3)), gridspec_kw={"width_ratios": [1.15, 1]})
    y = np.arange(len(comp))

    for i, (_, r) in enumerate(comp.iterrows()):
        bm = r["Margin_Baseline"]
        pm = r["Margin_Primary"]
        color = "#2b6cb0" if pm >= bm else "#c53030"
        ax1.plot([bm, pm], [i, i], color=color, linewidth=2.2, alpha=0.8)

    ax1.scatter(comp["Margin_Baseline"], y, color="#718096", s=55, zorder=3, label=f"{year} {office_baseline} Margin (Dem/Ind − GOP)")
    ax1.scatter(
        comp["Margin_Primary"],
        y,
        color=["#2b6cb0" if pm >= 0 else "#c53030" for pm in comp["Margin_Primary"]],
        s=75,
        zorder=4,
        label=f"{year} {office_primary} Margin (Dem/Ind − GOP)",
    )
    ax1.axvline(0, color="black", linestyle="--", linewidth=1.0)
    ax1.set_yticks(y)
    ax1.set_yticklabels(comp["State"], fontsize=9.5, fontweight="bold")
    ax1.set_xlabel("Statewide Vote Margin (%: Negative = GOP Lead, Positive = Dem/Ind Lead)", fontsize=10.5)
    ax1.set_title(f"{office_primary} Margin vs. {office_baseline} Margin on the Same Ballot", fontsize=12, fontweight="bold")
    ax1.legend(loc="lower right", frameon=True)

    bar_colors = ["#2b6cb0" if v >= 0 else "#c53030" for v in comp["Diff"]]
    bars = ax2.barh(y, comp["Diff"], color=bar_colors, height=0.7)
    ax2.axvline(0, color="black", linestyle="-", linewidth=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels(comp["State"], fontsize=9.5)
    ax2.set_xlabel(f"{office_primary} Margin Minus {office_baseline} Margin (% Points)", fontsize=10.5)
    ax2.set_title(f"Ticket-Splitting ({office_primary} vs. {office_baseline})", fontsize=12, fontweight="bold")
    min_d = min(-15.0, comp["Diff"].min() - 5.0)
    max_d = max(15.0, comp["Diff"].max() + 5.0)
    ax2.set_xlim(min_d, max_d)

    for b in bars:
        w = b.get_width()
        ha = "left" if w >= 0 else "right"
        off = 0.35 if w >= 0 else -0.35
        ax2.text(w + off, b.get_y() + b.get_height() / 2, f"{w:+.1f}%", va="center", ha=ha, fontsize=8.5, fontweight="bold")

    legend_elements = [
        Patch(facecolor="#2b6cb0", label=f"Dem {office_primary} Outran {office_baseline}"),
        Patch(facecolor="#c53030", label=f"GOP {office_primary} Outran {office_baseline}"),
    ]
    ax2.legend(handles=legend_elements, loc="lower right", frameon=True, fontsize=8.5)

    plt.suptitle(f"{year} Ticket-Splitting: {office_primary} vs. {office_baseline} Across {len(comp)} Reporting States", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    if out_fig:
        plt.savefig(out_fig, dpi=200, bbox_inches="tight")
        print(f"Saved Cross-Office Comparison plot to {out_fig}")
        plt.close()
    else:
        plt.show()
