"""
Deep-Dive Electoral Analytics & Visualizations for the 2026 Midterms.
Generates 5 multi-panel diagnostic figures using cached and canonical datasets
(zero network calls required):
  1. deep_dive_1_county_shifts.png: County Vote Shift Scatter & Distribution (Past Baseline vs. 2026)
  2. deep_dive_2_urban_rural_shift.png: Urban, Suburban, Small Town & Rural Shift Breakdown
  3. deep_dive_3_ticket_splitting.png: Split-Ticket Voting & Candidate Overperformance (Senate vs. House)
  4. deep_dive_4_wasted_votes.png: Deconstructing 'Votes per Seat' (Surplus vs. Lost Votes & Efficiency Gap)
  5. deep_dive_5_uncounted_votes.png: Outstanding Ballot Tracker (Where Are the Uncounted Votes?)
"""

import os
import sys
import json
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.schemas import standardize_party

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")


def load_county_shift_and_population_df() -> pd.DataFrame:
    """
    Combine 2026 county-level returns and NBC's historical baseline margins (from .cache)
    with 2024 Census county population data (from 2024/US_President_results.csv).
    """
    shift_rows = []
    cache_pattern = os.path.join(REPO_ROOT, "2026", ".cache", "*senate-results*.json")
    for f in sorted(glob.glob(cache_pattern)):
        if "national" in os.path.basename(f):
            continue
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        state = data.get("stateName", "Unknown")
        races = data.get("races") or []
        if not races:
            continue
        vsc = races[0].get("voteShiftCounties") or []
        areas = {a["name"]: a for a in (races[0].get("areas") or [])}
        for c in vsc:
            name = c.get("name", "")
            pct_in = float(c.get("percentIn", 0) or 0)
            curr_margin = float(c.get("margin", 0) or 0)
            curr_lead = c.get("marginLeadingParty", "")
            curr_dem_margin = curr_margin if curr_lead == "dem" else (-curr_margin if curr_lead == "rep" else 0.0)

            past_list = c.get("marginPastRaces") or []
            past = past_list[0] if past_list else {}
            past_margin = float(past.get("margin", 0) or 0)
            past_lead = past.get("leadingParty", "")
            past_dem_margin = past_margin if past_lead == "dem" else (-past_margin if past_lead == "rep" else 0.0)

            area_info = areas.get(name, {})
            votes = int(area_info.get("votes", 0) or 0)
            shift_rows.append({
                "State": state,
                "County": name,
                "Percent_In": pct_in,
                "Votes_2026": votes,
                "Past_Margin": past_dem_margin,
                "Margin_2026": curr_dem_margin,
                "Shift": curr_dem_margin - past_dem_margin,
            })

    df_shift = pd.DataFrame(shift_rows)

    pres_24_path = os.path.join(REPO_ROOT, "2024", "US_President_results.csv")
    if os.path.exists(pres_24_path) and not df_shift.empty:
        df_24 = pd.read_csv(pres_24_path)
        df_24["County_clean"] = df_24["County"].str.replace(r"\s*\d+\.?\d*% in", "", regex=True).str.strip()
        df_24["Population"] = pd.to_numeric(df_24["Population"], errors="coerce").fillna(0)
        df_24 = df_24.drop_duplicates(subset=["State", "County_clean"])
        df_shift = pd.merge(
            df_shift,
            df_24[["State", "County_clean", "Population"]],
            left_on=["State", "County"],
            right_on=["State", "County_clean"],
            how="left",
        )
        df_shift["Population"] = df_shift["Population"].fillna(0)
    else:
        df_shift["Population"] = 0

    return df_shift


def plot_1_county_shifts(df_shift: pd.DataFrame, out_fig: str = "2026/deep_dive_1_county_shifts.png"):
    """
    Plot 1: County-Level Margin Shift Scatter & Distribution.
    Left: Past Margin (X) vs. 2026 Senate Margin (Y), sized by votes cast.
    Right: Distribution of county shifts (2026 Margin - Past Margin).
    """
    rep = df_shift[(df_shift["Percent_In"] > 20) & (df_shift["Votes_2026"] > 0)].copy()
    if rep.empty:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw={"width_ratios": [1.3, 1]})

    # Left panel: Bubble scatter
    flipped_r_to_d = rep[(rep["Past_Margin"] < 0) & (rep["Margin_2026"] > 0)]
    held_d = rep[(rep["Past_Margin"] >= 0) & (rep["Margin_2026"] >= 0)]
    held_r = rep[(rep["Past_Margin"] <= 0) & (rep["Margin_2026"] <= 0)]
    flipped_d_to_r = rep[(rep["Past_Margin"] > 0) & (rep["Margin_2026"] < 0)]

    def sizes(sub):
        return np.clip(sub["Votes_2026"] / 1200.0, 12, 450)

    ax1.scatter(held_r["Past_Margin"], held_r["Margin_2026"], s=sizes(held_r), c="#e53e3e", alpha=0.45, edgecolors="none", label=f"Held GOP ({len(held_r)} counties)")
    ax1.scatter(held_d["Past_Margin"], held_d["Margin_2026"], s=sizes(held_d), c="#3182ce", alpha=0.50, edgecolors="none", label=f"Held Dem ({len(held_d)} counties)")
    ax1.scatter(flipped_r_to_d["Past_Margin"], flipped_r_to_d["Margin_2026"], s=sizes(flipped_r_to_d), c="#6b46c1", alpha=0.80, edgecolors="white", linewidth=0.6, label=f"Flipped GOP → Dem ({len(flipped_r_to_d)} counties)")
    if not flipped_d_to_r.empty:
        ax1.scatter(flipped_d_to_r["Past_Margin"], flipped_d_to_r["Margin_2026"], s=sizes(flipped_d_to_r), c="#dd6b20", alpha=0.80, edgecolors="white", linewidth=0.6, label=f"Flipped Dem → GOP ({len(flipped_d_to_r)} counties)")

    # 1:1 no-change line
    ax1.plot([-100, 100], [-100, 100], color="black", linestyle="--", linewidth=1.2, label="No Change Line (2026 = Past)")
    ax1.axhline(0, color="gray", linestyle=":", linewidth=0.9)
    ax1.axvline(0, color="gray", linestyle=":", linewidth=0.9)

    # Shade the R->D flip quadrant
    ax1.fill_between([-100, 0], 0, 100, color="#6b46c1", alpha=0.06)
    ax1.text(-50, 78, "FLIPPED\nGOP → DEM\nQUADRANT", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#553c9a")
    ax1.text(-55, -82, "Points ABOVE dashed line =\nShifted toward Democrats in 2026", ha="center", va="center", fontsize=9, style="italic", bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    ax1.set_xlim(-100, 100)
    ax1.set_ylim(-100, 100)
    ax1.set_xlabel("Past Baseline Margin (%: Negative = GOP, Positive = Dem)", fontsize=11)
    ax1.set_ylabel("2026 U.S. Senate Margin (%: Negative = GOP, Positive = Dem)", fontsize=11)
    ax1.set_title("County-by-County Margin Shift (Bubble Size = Total Votes)", fontsize=12.5, fontweight="bold")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=9.5)

    # Right panel: Distribution of shifts
    shifts = rep["Shift"].clip(-40, 50)
    median_shift = rep["Shift"].median()
    mean_shift = np.average(rep["Shift"], weights=rep["Votes_2026"])

    bins = np.linspace(-30, 45, 39)
    n, bins_out, patches = ax2.hist(shifts, bins=bins, edgecolor="white", alpha=0.85)
    for patch, x_left in zip(patches, bins_out[:-1]):
        patch.set_facecolor("#2b6cb0" if x_left >= 0 else "#c53030")

    ax2.axvline(0, color="black", linestyle="-", linewidth=1.2, label="Zero Shift")
    ax2.axvline(median_shift, color="#1a365d", linestyle="--", linewidth=2.0, label=f"Median County Shift: {median_shift:+.1f}%")
    ax2.axvline(mean_shift, color="#6b46c1", linestyle="-.", linewidth=2.0, label=f"Vote-Weighted Shift: {mean_shift:+.1f}%")

    pct_shifted_dem = (rep["Shift"] > 0).mean() * 100
    ax2.set_xlabel("Net Margin Shift Toward Democrats (% Points)", fontsize=11)
    ax2.set_ylabel("Number of Counties", fontsize=11)
    ax2.set_title(f"Distribution of County Shifts ({pct_shifted_dem:.1f}% Shifted Blue)", fontsize=12.5, fontweight="bold")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=9.5)

    plt.suptitle(f"Deep Dive 1: The Anatomy of the 2026 County-Level Wave ({len(rep):,} Reporting Counties >20% In)", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_fig, dpi=200, bbox_inches="tight")
    print(f"Saved {out_fig}")
    plt.close()


def plot_2_urban_rural_shift(df_shift: pd.DataFrame, out_fig: str = "2026/deep_dive_2_urban_rural_shift.png"):
    """
    Plot 2: Urban vs. Suburban vs. Small Town vs. Rural Shift & Vote Volume.
    """
    m_rep = df_shift[(df_shift["Percent_In"] > 20) & (df_shift["Population"] > 0) & (df_shift["Votes_2026"] > 0)].copy()
    if m_rep.empty:
        return

    bins = [0, 25000, 100000, 500000, 100000000]
    labels = ["Rural\n(<25k pop)", "Small Town\n(25k–100k)", "Suburban\n(100k–500k)", "Large Urban\n(>500k pop)"]
    m_rep["Tier"] = pd.cut(m_rep["Population"], bins=bins, labels=labels)

    tier_stats = []
    for t in labels:
        sub = m_rep[m_rep["Tier"] == t]
        if sub.empty:
            continue
        w_past = np.average(sub["Past_Margin"], weights=sub["Votes_2026"])
        w_26 = np.average(sub["Margin_2026"], weights=sub["Votes_2026"])
        tier_stats.append({
            "Tier": t,
            "Counties": len(sub),
            "Votes": sub["Votes_2026"].sum(),
            "Past_Margin": w_past,
            "Margin_2026": w_26,
            "Shift": w_26 - w_past,
        })

    tdf = pd.DataFrame(tier_stats)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 6), gridspec_kw={"width_ratios": [1.25, 1]})

    x = np.arange(len(tdf))
    width = 0.35

    bars_past = ax1.bar(x - width / 2, tdf["Past_Margin"], width, label="Past Baseline Margin", color="#a0aec0", edgecolor="black", linewidth=0.6)
    bars_26 = ax1.bar(
        x + width / 2,
        tdf["Margin_2026"],
        width,
        label="2026 Senate Margin",
        color=["#2b6cb0" if v >= 0 else "#c53030" for v in tdf["Margin_2026"]],
        edgecolor="black",
        linewidth=0.6,
    )

    ax1.axhline(0, color="black", linewidth=1.1)
    ax1.set_xticks(x)
    ax1.set_xticklabels(tdf["Tier"], fontsize=10.5, fontweight="bold")
    ax1.set_ylabel("Vote-Weighted Margin (%: +Dem / -GOP)", fontsize=11)
    ax1.set_ylim(-38, 48)
    ax1.set_title("Partisan Margin by County Population Tier (Past vs. 2026)", fontsize=12.5, fontweight="bold")

    legend_elements = [
        Patch(facecolor="#a0aec0", edgecolor="black", label="Past Baseline Margin"),
        Patch(facecolor="#c53030", edgecolor="black", label="2026 Senate Margin (GOP Lead)"),
        Patch(facecolor="#2b6cb0", edgecolor="black", label="2026 Senate Margin (Dem Lead)"),
    ]
    ax1.legend(handles=legend_elements, loc="upper left", frameon=True, fontsize=9)

    for b in bars_past:
        v = b.get_height()
        va = "bottom" if v >= 0 else "top"
        offset = 1.0 if v >= 0 else -1.5
        ax1.text(b.get_x() + b.get_width() / 2, v + offset, f"{v:+.1f}%", ha="center", va=va, fontsize=9, color="#4a5568", fontweight="bold")

    for i, b in enumerate(bars_26):
        v = b.get_height()
        va = "bottom" if v >= 0 else "top"
        offset = 1.0 if v >= 0 else -1.5
        ax1.text(b.get_x() + b.get_width() / 2, v + offset, f"{v:+.1f}%", ha="center", va=va, fontsize=9.5, fontweight="bold")
        shift_v = tdf.loc[i, "Shift"]
        box_y = max(v, tdf.loc[i, "Past_Margin"]) + 6.5 if v >= 0 else 6.0
        ax1.annotate(
            f"Shift: {shift_v:+.1f}%",
            xy=(x[i] + width / 2, v if v >= 0 else 0),
            xytext=(x[i], box_y),
            ha="center",
            fontsize=8.5,
            fontweight="bold",
            color="#1a365d",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#ebf8ff", edgecolor="#90cdf4"),
        )

    # Right panel: Total votes cast by tier + counties count
    tot_votes_all = tdf["Votes"].sum()
    bars_v = ax2.bar(x, tdf["Votes"] / 1e6, width=0.5, color=["#e53e3e", "#dd6b20", "#6b46c1", "#2b6cb0"], edgecolor="black", linewidth=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(tdf["Tier"], fontsize=10.5, fontweight="bold")
    ax2.set_ylabel("Total Votes Cast (Millions)", fontsize=11)
    ax2.set_ylim(0, (tdf["Votes"].max() / 1e6) * 1.25)
    ax2.set_title("Where the Votes Are: Volume & County Count by Tier", fontsize=12.5, fontweight="bold")

    for i, b in enumerate(bars_v):
        v_m = b.get_height()
        share = (tdf.loc[i, "Votes"] / tot_votes_all) * 100
        c_cnt = tdf.loc[i, "Counties"]
        ax2.text(
            b.get_x() + b.get_width() / 2,
            v_m + 0.4,
            f"{v_m:.1f}M votes\n({share:.1f}% of vote)\n[{c_cnt} counties]",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    sub_shift = tdf.loc[tdf["Tier"].str.startswith("Suburban"), "Shift"].iloc[0] if any(tdf["Tier"].str.startswith("Suburban")) else 0.0
    urb_shift = tdf.loc[tdf["Tier"].str.startswith("Large Urban"), "Shift"].iloc[0] if any(tdf["Tier"].str.startswith("Large Urban")) else 0.0
    plt.suptitle(f"Deep Dive 2: How Suburban Flip ({sub_shift:+.1f}%) & Urban Surge ({urb_shift:+.1f}%) Drove the 2026 Results", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_fig, dpi=200, bbox_inches="tight")
    print(f"Saved {out_fig}")
    plt.close()


def plot_3_ticket_splitting(
    senate_csv: str = "2026/US_Senate_state_results.csv",
    house_csv: str = "2026/US_House_results.csv",
    out_fig: str = "2026/deep_dive_3_ticket_splitting.png",
):
    """
    Plot 3: Ticket-Splitting & Candidate Overperformance (2026 Senate Margin vs. 2026 House Margin).
    """
    if not (os.path.exists(senate_csv) and os.path.exists(house_csv)):
        return

    sen = pd.read_csv(senate_csv)
    house = pd.read_csv(house_csv)
    house["Clean Party"] = house["Party"].apply(standardize_party)

    # Compute statewide House popular vote margin (Dem - GOP)
    h_state = house.groupby(["State", "Clean Party"])["Total Votes"].sum().unstack(fill_value=0)
    h_state["Total"] = h_state.sum(axis=1)
    h_state = h_state[h_state["Total"] > 0].copy()
    h_state["House_Dem_Pct"] = h_state.get("Democrat", 0) / h_state["Total"] * 100.0
    h_state["House_GOP_Pct"] = h_state.get("Republican", 0) / h_state["Total"] * 100.0
    h_state["House_Margin"] = h_state["House_Dem_Pct"] - h_state["House_GOP_Pct"]

    sen = sen[sen["Percent Reporting"] > 20].copy()
    # Read top single Independent candidate vote share from cache if available
    top_ind_map = {}
    cache_pattern = os.path.join(REPO_ROOT, "2026", ".cache", "*senate-results*.json")
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
                top_ind_map[st] = (best.get("name", "Ind"), float(best.get("percentVote", 0) or 0))
        except Exception:
            pass

    sen["Top_Ind_Pct"] = sen["State"].map(lambda s: top_ind_map.get(s, ("", 0.0))[1])
    sen["Top_Ind_Pct"] = np.where(sen["Top_Ind_Pct"] > 0, sen["Top_Ind_Pct"], sen["Other Pct"])
    sen["Is_Ind"] = sen["Top_Ind_Pct"] > sen["Dem Pct"]
    sen["Challenger_Pct"] = np.maximum(sen["Dem Pct"], sen["Top_Ind_Pct"])
    sen["Sen_Margin"] = sen["Challenger_Pct"] - sen["GOP Pct"]

    comp = pd.merge(sen, h_state[["House_Margin"]], on="State", how="inner")
    comp["Overperformance"] = comp["Sen_Margin"] - comp["House_Margin"]
    comp["Label"] = comp.apply(
        lambda r: f"{r['State']} (Ind)" if r["Is_Ind"] else str(r["State"]),
        axis=1,
    )
    comp = comp.sort_values("Overperformance", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 8.5), gridspec_kw={"width_ratios": [1.15, 1]})

    # Left panel: Dumbbell plot of House Margin vs. Senate Margin by state
    y = np.arange(len(comp))
    for i, (_, r) in enumerate(comp.iterrows()):
        hm = r["House_Margin"]
        sm = r["Sen_Margin"]
        color = "#805ad5" if r["Is_Ind"] else ("#2b6cb0" if sm > hm else "#c53030")
        ax1.plot([hm, sm], [i, i], color=color, linewidth=2.2, alpha=0.8)

    ax1.scatter(comp["House_Margin"], y, color="#718096", s=55, zorder=3, label="2026 U.S. House Margin (Dem − GOP)")
    ax1.scatter(
        comp["Sen_Margin"],
        y,
        color=["#805ad5" if ind else ("#2b6cb0" if sm >= 0 else "#c53030") for ind, sm in zip(comp["Is_Ind"], comp["Sen_Margin"])],
        s=75,
        zorder=4,
        label="2026 U.S. Senate Margin (Challenger − GOP)",
    )

    ax1.axvline(0, color="black", linestyle="--", linewidth=1.0)
    ax1.set_yticks(y)
    ax1.set_yticklabels(comp["Label"], fontsize=9.5, fontweight="bold")
    ax1.set_xlabel("Statewide Vote Margin (%: Negative = GOP Lead, Positive = Dem/Ind Lead)", fontsize=10.5)
    ax1.set_title("Senate Margin vs. House Margin on the Same Ballot", fontsize=12, fontweight="bold")
    ax1.legend(loc="lower right", frameon=True)

    # Right panel: Net Candidate Overperformance (Senate Margin - House Margin)
    bar_colors = [
        "#805ad5" if ind else ("#2b6cb0" if v >= 0 else "#c53030")
        for ind, v in zip(comp["Is_Ind"], comp["Overperformance"])
    ]
    bars = ax2.barh(y, comp["Overperformance"], color=bar_colors, height=0.7)
    ax2.axvline(0, color="black", linestyle="-", linewidth=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels(comp["Label"], fontsize=9.5)
    ax2.set_xlabel("Senate Overperformance vs. House Baseline (% Points)", fontsize=10.5)
    ax2.set_title("Ticket-Splitting: Who Outran Their Party's House Baseline?", fontsize=12, fontweight="bold")
    ax2.set_xlim(-16, 15)

    for b in bars:
        w = b.get_width()
        ha = "left" if w >= 0 else "right"
        off = 0.3 if w >= 0 else -0.3
        ax2.text(w + off, b.get_y() + b.get_height() / 2, f"{w:+.1f}%", va="center", ha=ha, fontsize=8.5, fontweight="bold")

    legend_elements = [
        Patch(facecolor="#2b6cb0", label="Dem Senate Nominee Outran House Dems"),
        Patch(facecolor="#805ad5", label="Independent Senate Challenger"),
        Patch(facecolor="#c53030", label="GOP Senate Nominee Outran House GOP (e.g. Collins in ME)"),
    ]
    ax2.legend(handles=legend_elements, loc="lower right", frameon=True, fontsize=8.5)

    plt.suptitle("Deep Dive 3: Ticket-Splitting & Candidate Overperformance Across 34 Reporting Senate States", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(out_fig, dpi=200, bbox_inches="tight")
    print(f"Saved {out_fig}")
    plt.close()


def plot_4_wasted_votes(house_csv: str = "2026/US_House_results.csv", out_fig: str = "2026/deep_dive_4_wasted_votes.png"):
    """
    Plot 4: Deconstructing 'Votes per Seat' — Effective vs. Surplus (Packed) vs. Lost (Cracked) Votes,
    plus the District Winning Margin Distribution.
    """
    if not os.path.exists(house_csv):
        return

    h26 = pd.read_csv(house_csv)
    h26["Clean Party"] = h26["Party"].apply(standardize_party)

    records = []
    for (s, d), grp in h26.groupby(["State", "District"]):
        pct_rep = float(grp["Percent Reporting"].iloc[0] or 0)
        if pct_rep == 0 or grp["Total Votes"].sum() == 0:
            continue
        dem_v = grp[grp["Clean Party"] == "Democrat"]["Total Votes"].sum()
        gop_v = grp[grp["Clean Party"] == "Republican"]["Total Votes"].sum()
        two_party = dem_v + gop_v
        if two_party == 0:
            continue
        win_thresh = int(two_party // 2) + 1
        dem_share = (dem_v / two_party) * 100.0

        if dem_v > gop_v:
            records.append({
                "State": s, "District": d, "Dem_Share": dem_share,
                "Dem_Eff": min(dem_v, win_thresh), "Dem_Surplus": max(0, dem_v - win_thresh), "Dem_Lost": 0,
                "GOP_Eff": 0, "GOP_Surplus": 0, "GOP_Lost": gop_v,
                "Two_Party": two_party,
            })
        else:
            records.append({
                "State": s, "District": d, "Dem_Share": dem_share,
                "Dem_Eff": 0, "Dem_Surplus": 0, "Dem_Lost": dem_v,
                "GOP_Eff": min(gop_v, win_thresh), "GOP_Surplus": max(0, gop_v - win_thresh), "GOP_Lost": 0,
                "Two_Party": two_party,
            })

    wdf = pd.DataFrame(records)
    if wdf.empty:
        return

    de, ds, dl = wdf["Dem_Eff"].sum() / 1e6, wdf["Dem_Surplus"].sum() / 1e6, wdf["Dem_Lost"].sum() / 1e6
    ge, gs, gl = wdf["GOP_Eff"].sum() / 1e6, wdf["GOP_Surplus"].sum() / 1e6, wdf["GOP_Lost"].sum() / 1e6
    dem_seats = int((wdf["Dem_Share"] > 50).sum())
    gop_seats = int((wdf["Dem_Share"] <= 50).sum())
    tot_two_party = wdf["Two_Party"].sum()
    eff_gap = (((ds + dl) - (gs + gl)) * 1e6 / tot_two_party) * 100.0 if tot_two_party > 0 else 0.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.05, 1.2]})

    # Left panel: Stacked bar of Effective, Surplus (Packed), and Lost (Cracked) votes
    parties = [f"Democrat\n({dem_seats} Seats Won/Lead)", f"Republican\n({gop_seats} Seats Won/Lead)"]
    eff_vals = [de, ge]
    surplus_vals = [ds, gs]
    lost_vals = [dl, gl]

    b1 = ax1.bar(parties, eff_vals, width=0.48, label="Effective Votes (50% + 1 needed to win seat)", color=["#1f4e79", "#900c3f"])
    b2 = ax1.bar(parties, surplus_vals, bottom=eff_vals, width=0.48, label="Surplus 'Packed' Votes (Excess in safe wins)", color=["#4299e1", "#fc8181"], hatch="//")
    b3 = ax1.bar(
        parties,
        lost_vals,
        bottom=[eff_vals[i] + surplus_vals[i] for i in range(2)],
        width=0.48,
        label="Lost 'Cracked' Votes (Cast in losing districts)",
        color=["#cbd5e0", "#fed7d7"],
        edgecolor="gray",
        hatch="..",
    )

    ax1.set_ylabel("Popular Votes Cast (Millions)", fontsize=11)
    ax1.set_ylim(0, max(de + ds + dl, ge + gs + gl) * 1.18)
    ax1.set_title("Deconstructing Popular Votes: Effective vs. Wasted", fontsize=12.5, fontweight="bold")
    ax1.legend(loc="upper right", frameon=True, fontsize=9)

    for i in range(2):
        ax1.text(i, eff_vals[i] / 2, f"Effective:\n{eff_vals[i]:.1f}M", ha="center", va="center", color="white", fontweight="bold", fontsize=9.5)
        ax1.text(i, eff_vals[i] + surplus_vals[i] / 2, f"Surplus (Packed): {surplus_vals[i]:.1f}M", ha="center", va="center", color="black", fontweight="bold", fontsize=8.5)
        ax1.text(i, eff_vals[i] + surplus_vals[i] + lost_vals[i] / 2, f"Lost (Cracked):\n{lost_vals[i]:.1f}M", ha="center", va="center", color="#2d3748", fontweight="bold", fontsize=9)
        tot = eff_vals[i] + surplus_vals[i] + lost_vals[i]
        ax1.text(i, tot + 1.0, f"Total: {tot:.1f}M", ha="center", va="bottom", fontweight="bold", fontsize=10.5)

    # Right panel: Histogram of District Two-Party Vote Share
    bins = np.linspace(0, 100, 26)
    n, bins_out, patches = ax2.hist(wdf["Dem_Share"], bins=bins, edgecolor="white", alpha=0.88)
    for patch, x_left in zip(patches, bins_out[:-1]):
        if x_left < 50:
            patch.set_facecolor("#c53030" if x_left >= 30 else "#742a2a")
        else:
            patch.set_facecolor("#2b6cb0" if x_left < 70 else "#1a365d")

    ax2.axvline(50, color="black", linestyle="--", linewidth=1.8, label="50% Win Threshold")
    ax2.axvspan(50, 60, color="#ebf8ff", alpha=0.5, label="Efficient Narrow Wins (50%–60%)")
    ax2.axvspan(70, 100, color="#bee3f8", alpha=0.35, label="Urban Packing Zone (>70% Dem)")

    ax2.set_xlabel("Democratic Two-Party Vote Share in District (%)", fontsize=11)
    ax2.set_ylabel("Number of Congressional Districts", fontsize=11)
    ratio = ds / gs if gs > 0 else 0
    ax2.set_title(f"Why Dems Have {ratio:.1f}x More 'Packed' Surplus Votes ({ds:.1f}M vs. {gs:.1f}M)", fontsize=12.5, fontweight="bold")
    ax2.legend(loc="upper left", frameon=True, fontsize=9)

    plt.suptitle(f"Deep Dive 4: Explaining 'Votes per Seat' & The {eff_gap:+.2f}% Efficiency Gap Across {len(wdf)} Reporting Districts", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_fig, dpi=200, bbox_inches="tight")
    print(f"Saved {out_fig}")
    plt.close()


def plot_5_uncounted_votes(
    county_csv: str = "2026/US_Senate_county_results.csv",
    state_csv: str = "2026/US_Senate_state_results.csv",
    out_fig: str = "2026/deep_dive_5_uncounted_votes.png",
):
    """
    Plot 5: Where Are the Remaining Uncounted Votes?
    Estimates uncounted votes by county and aggregates by state and partisan lean of the county.
    """
    if not (os.path.exists(county_csv) and os.path.exists(state_csv)):
        return

    df_c = pd.read_csv(county_csv)
    df_s = pd.read_csv(state_csv)

    # Filter to counties with >0% reporting so we can extrapolate remaining votes
    rep = df_c[(df_c["Percent Reporting"] > 0) & (df_c["Percent Reporting"] < 100)].copy()
    if rep.empty:
        return

    rep["Est_Total"] = rep["Total Votes"] / (rep["Percent Reporting"] / 100.0)
    rep["Uncounted_Votes"] = np.maximum(0, rep["Est_Total"] - rep["Total Votes"])

    # Classify county partisan lean based on current leader in that county
    def county_lean(r):
        d, g, o = r["Dem Pct"], r["GOP Pct"], r["Other Pct"]
        if d >= g and d >= o:
            return "Dem-Leading Counties"
        elif g >= d and g >= o:
            return "GOP-Leading Counties"
        return "Ind-Leading Counties"

    rep["Lean"] = rep.apply(county_lean, axis=1)

    state_uncounted = rep.groupby(["State", "Lean"])["Uncounted_Votes"].sum().unstack(fill_value=0)
    state_uncounted["Total_Uncounted"] = state_uncounted.sum(axis=1)

    # Merge state call status
    state_status = df_s.set_index("State")[["Winner", "Percent Reporting"]]
    state_uncounted = state_uncounted.join(state_status, how="left")

    # Top 15 states by remaining uncounted votes
    top15 = state_uncounted.sort_values("Total_Uncounted", ascending=True).tail(15)

    fig, ax = plt.subplots(figsize=(11, 7))
    y_labels = [
        f"{st} ({row['Percent Reporting']:.0f}% in) {'[CALLED]' if pd.notna(row['Winner']) and str(row['Winner']).strip() else '[UNCALLED]'}"
        for st, row in top15.iterrows()
    ]

    d_unc = top15.get("Dem-Leading Counties", pd.Series(0, index=top15.index)) / 1e6
    g_unc = top15.get("GOP-Leading Counties", pd.Series(0, index=top15.index)) / 1e6
    i_unc = top15.get("Ind-Leading Counties", pd.Series(0, index=top15.index)) / 1e6

    ax.barh(y_labels, d_unc, color="#2b6cb0", label="Uncounted Votes in Dem-Leading Counties", height=0.68)
    ax.barh(y_labels, g_unc, left=d_unc, color="#c53030", label="Uncounted Votes in GOP-Leading Counties", height=0.68)
    if i_unc.sum() > 0:
        ax.barh(y_labels, i_unc, left=d_unc + g_unc, color="#805ad5", label="Uncounted Votes in Ind-Leading Counties", height=0.68)

    for idx, (st, row) in enumerate(top15.iterrows()):
        tot_m = row["Total_Uncounted"] / 1e6
        ax.text(tot_m + 0.04, idx, f"{row['Total_Uncounted']:,.0f} votes left", va="center", ha="left", fontsize=9, fontweight="bold")

    tot_rem_m = state_uncounted["Total_Uncounted"].sum() / 1e6
    ax.set_xlim(0, (top15["Total_Uncounted"].max() / 1e6) * 1.22)
    ax.set_xlabel("Estimated Remaining Uncounted Votes (Millions)", fontsize=11)
    ax.set_title(f"Deep Dive 5: Where Are the Remaining ~{tot_rem_m:.1f}M Uncounted Senate Ballots?", fontsize=13.5, fontweight="bold")
    ax.legend(loc="lower right", frameon=True, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(out_fig, dpi=200, bbox_inches="tight")
    print(f"Saved {out_fig}")
    plt.close()


if __name__ == "__main__":
    df_shift = load_county_shift_and_population_df()
    plot_1_county_shifts(df_shift)
    plot_2_urban_rural_shift(df_shift)
    plot_3_ticket_splitting()
    plot_4_wasted_votes()
    plot_5_uncounted_votes()
