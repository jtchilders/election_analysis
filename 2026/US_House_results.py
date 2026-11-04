"""
Scrape 2026 US House of Representatives election results from NBC News.
Uses PoliteFetcher for polite rate-limiting, randomized delays, and disk caching
to avoid getting blocked. Outputs standard canonical CSV formats defined in common.schemas.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.schemas import (
    DISTRICT_COLUMNS,
    standardize_party,
    clean_percentage,
    clean_int,
)
from common.fetcher import PoliteFetcher

YEAR = 2026
OFFICE = "House"

BATTLEGROUND_HOUSE_STATES = [
    "California",
    "New York",
    "Pennsylvania",
    "Michigan",
    "Virginia",
    "Arizona",
    "North Carolina",
    "Georgia",
    "Ohio",
    "Texas",
]


def parse_state_house_districts(data: dict, state_name: str) -> list[dict]:
    """Parse district and candidate rows from state house data into canonical rows."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []

    races = data.get("races", [])
    if not races:
        return records

    map_data = races[0].get("mapData", {})

    for dist_code, dist_info in sorted(map_data.items()):
        try:
            dist_num = int(dist_code)
            dist_name = f"District {dist_num}"
        except ValueError:
            dist_name = f"District {dist_code}"

        percent_reporting = clean_percentage(dist_info.get("percentIn", 0))

        for cand in dist_info.get("candidates", []):
            candidate_name = cand.get("name", "Unknown")
            party = standardize_party(cand.get("party"))
            votes = clean_int(cand.get("votes", 0))
            pct = clean_percentage(cand.get("percentVote", 0))
            incumbent = bool(cand.get("isIncumbent", False))
            winner = bool(cand.get("isWinner", False))

            records.append({
                "Year": YEAR,
                "Office": OFFICE,
                "State": state_name,
                "District": dist_name,
                "Candidate": candidate_name,
                "Party": party,
                "Percentage of Votes (%)": pct,
                "Total Votes": votes,
                "Incumbent": incumbent,
                "Percent Reporting": percent_reporting,
                "Winner": winner,
                "Updated": now,
            })

    return records


def scrape_house(
    states: list[str] = None,
    cache_ttl_minutes: float = 30.0,
    force_refresh: bool = False,
    min_delay: float = 2.0,
    max_delay: float = 4.0,
) -> pd.DataFrame:
    """Politely fetch and parse House results."""
    fetcher = PoliteFetcher(
        cache_dir=os.path.join(REPO_ROOT, "2026", ".cache"),
        cache_ttl_minutes=cache_ttl_minutes,
        min_delay=min_delay,
        max_delay=max_delay,
    )

    manifest_url = "https://www.nbcnews.com/firecracker/api/v2/national-results/2026-elections/house-results"
    manifest_data = fetcher.fetch(manifest_url, is_json=True, force_refresh=force_refresh)
    all_states = manifest_data.get("tableData", {}).get("states", [])

    if states:
        selected = [s.strip().lower() for s in states]
        target_states = [
            s for s in all_states
            if s["stateName"].lower() in selected or s["stateAbbr"].lower() in selected
        ]
    else:
        target_states = all_states

    all_records = []
    print(f"Politely scraping House results for {len(target_states)} states (cache TTL: {cache_ttl_minutes}m)...")

    for idx, s_meta in enumerate(target_states, 1):
        state_name = s_meta["stateName"]
        state_slug = state_name.lower().replace(" ", "-")
        url = f"https://www.nbcnews.com/firecracker/api/v2/state-results/2026-elections/{state_slug}-house-results"

        print(f"[{idx}/{len(target_states)}] Checking {state_name} ({s_meta.get('totalSeats', '?')} seats)...")
        try:
            state_data = fetcher.fetch(url, is_json=True, force_refresh=force_refresh)
            records = parse_state_house_districts(state_data, state_name)
            all_records.extend(records)
        except Exception as e:
            print(f"  Error processing {state_name}: {e}")

    df = pd.DataFrame(all_records, columns=DISTRICT_COLUMNS) if all_records else pd.DataFrame(columns=DISTRICT_COLUMNS)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Politely extract 2026 House election results into canonical format")
    parser.add_argument("--states", nargs="+", help="Specific states (e.g. Alabama Pennsylvania)")
    parser.add_argument("--all", action="store_true", help="Scrape all 50 states (435 seats)")
    parser.add_argument("--battlegrounds", action="store_true", help="Scrape competitive House battlegrounds")
    parser.add_argument("--cache-ttl", type=float, default=30.0, help="Cache lifetime in minutes (default 30m)")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache and re-fetch live data")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum jitter delay in seconds")
    parser.add_argument("--delay-max", type=float, default=4.0, help="Maximum jitter delay in seconds")
    parser.add_argument("--out-csv", type=str, default="2026/US_House_results.csv", help="Output CSV path")

    args = parser.parse_args()

    if args.all:
        target_states = None
    elif args.battlegrounds:
        target_states = BATTLEGROUND_HOUSE_STATES
    elif args.states:
        target_states = args.states
    else:
        target_states = ["Alabama", "Pennsylvania", "Georgia"]

    df = scrape_house(
        states=target_states,
        cache_ttl_minutes=args.cache_ttl,
        force_refresh=args.force_refresh,
        min_delay=args.delay_min,
        max_delay=args.delay_max,
    )

    if not df.empty:
        df.to_csv(args.out_csv, index=False)
        print(f"\nSaved {len(df)} candidate records to {args.out_csv}")
        print("\nSample Preview:")
        print(df.head(6)[["Year", "Office", "State", "District", "Candidate", "Party", "Percentage of Votes (%)", "Total Votes"]])
    else:
        print("No records extracted.")
