"""
Scrape 2026 US Senate midterm election results from NBC News.
Uses PoliteFetcher for polite rate-limiting, randomized delays, and disk caching
to avoid getting blocked. Outputs standard canonical CSV formats defined in common.schemas.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup

# Add repository root to python path to import common
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.schemas import (
    COUNTY_COLUMNS,
    STATE_SUMMARY_COLUMNS,
    standardize_party,
    clean_percentage,
    clean_int,
)
from common.fetcher import PoliteFetcher

YEAR = 2026
OFFICE = "Senate"

BATTLEGROUND_SENATE_STATES = [
    "Georgia",
    "North Carolina",
    "Maine",
    "Michigan",
    "Texas",
    "New Hampshire",
    "Iowa",
    "Ohio",
]


def parse_state_data(data: dict) -> tuple[list[dict], dict]:
    """Parse state payload (from API or HTML __NEXT_DATA__) into canonical records."""
    state_name = data.get("stateName", "Unknown")
    races = data.get("races", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    county_records = []
    state_summary = None

    for race in races:
        summary = race.get("summary", {})
        candidates = summary.get("candidates", [])

        # Identify Dem and GOP candidates from summary
        dem_cand = next((c for c in candidates if (c.get("party") or "").lower() == "dem"), {})
        gop_cand = next((c for c in candidates if (c.get("party") or "").lower() == "gop"), {})

        # Compute other votes / pcts
        other_votes = sum(c.get("votes", 0) for c in candidates if (c.get("party") or "").lower() not in ["dem", "gop"])
        other_pct = sum(clean_percentage(c.get("percentVote", 0)) for c in candidates if (c.get("party") or "").lower() not in ["dem", "gop"])

        winner_cand = next((c for c in candidates if c.get("isWinner")), {})

        state_summary = {
            "Year": YEAR,
            "Office": OFFICE,
            "State": state_name,
            "Percent Reporting": clean_percentage(summary.get("percentIn", 0)),
            "Dem Candidate": dem_cand.get("name", ""),
            "Dem Votes": clean_int(dem_cand.get("votes", 0)),
            "Dem Pct": clean_percentage(dem_cand.get("percentVote", 0)),
            "GOP Candidate": gop_cand.get("name", ""),
            "GOP Votes": clean_int(gop_cand.get("votes", 0)),
            "GOP Pct": clean_percentage(gop_cand.get("percentVote", 0)),
            "Other Votes": clean_int(other_votes),
            "Other Pct": clean_percentage(other_pct),
            "Winner": winner_cand.get("name", ""),
            "Winner Party": standardize_party(winner_cand.get("party")),
            "Updated": now,
        }

        # County-level records
        for area in race.get("areas", []):
            county_name = area.get("name", "")
            percent_in = clean_percentage(area.get("percentIn", 0))
            total_votes = clean_int(area.get("votes", 0))

            area_candidates = area.get("candidates", [])
            area_dem = next((c for c in area_candidates if (c.get("party") or "").lower() == "dem"), {})
            area_gop = next((c for c in area_candidates if (c.get("party") or "").lower() == "gop"), {})

            c_other_votes = sum(clean_int(c.get("votes", 0)) for c in area_candidates if (c.get("party") or "").lower() not in ["dem", "gop"])
            c_other_pct = sum(clean_percentage(c.get("percentVote", 0)) for c in area_candidates if (c.get("party") or "").lower() not in ["dem", "gop"])

            c_winner = next((c for c in area_candidates if c.get("isWinner")), {})

            county_rec = {
                "Year": YEAR,
                "Office": OFFICE,
                "State": state_name,
                "County": county_name,
                "Percent Reporting": percent_in,
                "Total Votes": total_votes,
                "Dem Candidate": dem_cand.get("name", area_dem.get("name", "")),
                "Dem Votes": clean_int(area_dem.get("votes", 0)),
                "Dem Pct": clean_percentage(area_dem.get("percentVote", 0)),
                "GOP Candidate": gop_cand.get("name", area_gop.get("name", "")),
                "GOP Votes": clean_int(area_gop.get("votes", 0)),
                "GOP Pct": clean_percentage(area_gop.get("percentVote", 0)),
                "Other Votes": c_other_votes,
                "Other Pct": clean_percentage(c_other_pct),
                "Winner": c_winner.get("name", ""),
                "Winner Party": standardize_party(c_winner.get("party")),
                "Updated": now,
            }
            county_records.append(county_rec)

    return county_records, state_summary


def scrape_senate(
    states: list[str] = None,
    method: str = "api",
    cache_ttl_minutes: float = 30.0,
    force_refresh: bool = False,
    min_delay: float = 2.0,
    max_delay: float = 4.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Politely fetch and parse Senate results."""
    fetcher = PoliteFetcher(
        cache_dir=os.path.join(REPO_ROOT, "2026", ".cache"),
        cache_ttl_minutes=cache_ttl_minutes,
        min_delay=min_delay,
        max_delay=max_delay,
    )

    # 1. Fetch manifest of 2026 Senate races
    manifest_url = "https://www.nbcnews.com/firecracker/api/v2/national-results/2026-elections/senate-results"
    manifest_data = fetcher.fetch(manifest_url, is_json=True, force_refresh=force_refresh)
    all_states = manifest_data.get("tableData", {}).get("states", [])

    if states:
        selected = [s.strip().lower() for s in states]
        target_races = [
            s for s in all_states
            if s["stateName"].lower() in selected or s["stateAbbr"].lower() in selected
        ]
    else:
        target_races = all_states

    all_counties = []
    all_summaries = []

    print(f"Politely scraping Senate results for {len(target_races)} races (cache TTL: {cache_ttl_minutes}m)...")
    for idx, r_meta in enumerate(target_races, 1):
        state_name = r_meta["stateName"]
        state_slug = state_name.lower().replace(" special", "").replace(" ", "-")
        is_special = "special" in r_meta.get("href", "").lower()
        election_segment = "2026-special-elections" if is_special else "2026-elections"

        print(f"[{idx}/{len(target_races)}] Checking {state_name} ({state_slug})...")

        if method == "api":
            url = f"https://www.nbcnews.com/firecracker/api/v2/state-results/{election_segment}/{state_slug}-senate-results"
            try:
                data = fetcher.fetch(url, is_json=True, force_refresh=force_refresh)
                counties, summary = parse_state_data(data)
                all_counties.extend(counties)
                if summary:
                    all_summaries.append(summary)
            except Exception as e:
                print(f"  Error processing {state_name}: {e}")
        else:
            url = f"https://www.nbcnews.com/politics/{election_segment}/{state_slug}-senate-results"
            try:
                html = fetcher.fetch(url, is_json=False, force_refresh=force_refresh)
                soup = BeautifulSoup(html, "html.parser")
                next_tag = soup.find("script", id="__NEXT_DATA__")
                if next_tag and next_tag.string:
                    props = json.loads(next_tag.string)["props"]["pageProps"]
                    counties, summary = parse_state_data(props)
                    all_counties.extend(counties)
                    if summary:
                        all_summaries.append(summary)
            except Exception as e:
                print(f"  Error processing {state_name}: {e}")

    county_df = pd.DataFrame(all_counties, columns=COUNTY_COLUMNS) if all_counties else pd.DataFrame(columns=COUNTY_COLUMNS)
    state_df = pd.DataFrame(all_summaries, columns=STATE_SUMMARY_COLUMNS) if all_summaries else pd.DataFrame(columns=STATE_SUMMARY_COLUMNS)
    return county_df, state_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Politely extract 2026 Senate results into canonical format")
    parser.add_argument("--states", nargs="+", help="Specific states (e.g. Alabama Georgia)")
    parser.add_argument("--all", action="store_true", help="Scrape all 35 Senate races")
    parser.add_argument("--battlegrounds", action="store_true", help="Scrape battleground Senate states")
    parser.add_argument("--method", choices=["api", "html", "local"], default="api", help="Data access method")
    parser.add_argument("--local-file", type=str, default="2026/sample_alabama.html", help="Local HTML file path")
    parser.add_argument("--cache-ttl", type=float, default=30.0, help="Cache lifetime in minutes (default 30m)")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache and re-fetch live data")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum jitter delay in seconds")
    parser.add_argument("--delay-max", type=float, default=4.0, help="Maximum jitter delay in seconds")
    parser.add_argument("--out-county", type=str, default="2026/US_Senate_county_results.csv", help="County CSV path")
    parser.add_argument("--out-state", type=str, default="2026/US_Senate_state_results.csv", help="Statewide CSV path")

    args = parser.parse_args()

    if args.method == "local":
        with open(args.local_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        props = json.loads(soup.find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]
        counties, summary = parse_state_data(props)
        county_df = pd.DataFrame(counties, columns=COUNTY_COLUMNS)
        state_df = pd.DataFrame([summary], columns=STATE_SUMMARY_COLUMNS) if summary else pd.DataFrame(columns=STATE_SUMMARY_COLUMNS)
    else:
        if args.all:
            target_states = None
        elif args.battlegrounds:
            target_states = BATTLEGROUND_SENATE_STATES
        elif args.states:
            target_states = args.states
        else:
            target_states = ["Alabama"]

        county_df, state_df = scrape_senate(
            states=target_states,
            method=args.method,
            cache_ttl_minutes=args.cache_ttl,
            force_refresh=args.force_refresh,
            min_delay=args.delay_min,
            max_delay=args.delay_max,
        )

    if not county_df.empty:
        county_df.to_csv(args.out_county, index=False)
        print(f"\nSaved {len(county_df)} county records to {args.out_county}")
    if not state_df.empty:
        state_df.to_csv(args.out_state, index=False)
        print(f"Saved {len(state_df)} statewide records to {args.out_state}")
