"""
Convenience script to politely refresh all 2026 midterm datasets (Senate, Governor, House)
from NBC News into canonical CSV formats.
"""

import os
import sys
import argparse

DIR_2026 = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(DIR_2026, ".."))
for p in (DIR_2026, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from US_Senate_results import scrape_senate
from US_Governor_results import scrape_governor
from US_House_results import scrape_house


def main():
    parser = argparse.ArgumentParser(description="Politely update all 2026 Senate, Governor, and House CSVs")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache and fetch latest live results")
    parser.add_argument("--delay-min", type=float, default=0.9, help="Minimum jitter delay in seconds")
    parser.add_argument("--delay-max", type=float, default=1.5, help="Maximum jitter delay in seconds")
    args = parser.parse_args()

    sen_county, sen_state = scrape_senate(
        states=None,
        force_refresh=args.force_refresh,
        min_delay=args.delay_min,
        max_delay=args.delay_max,
    )
    if not sen_county.empty:
        sen_county.to_csv("2026/US_Senate_county_results.csv", index=False)
    if not sen_state.empty:
        sen_state.to_csv("2026/US_Senate_state_results.csv", index=False)

    gov_county, gov_state = scrape_governor(
        states=None,
        force_refresh=args.force_refresh,
        min_delay=args.delay_min,
        max_delay=args.delay_max,
    )
    if not gov_county.empty:
        gov_county.to_csv("2026/US_Governor_county_results.csv", index=False)
    if not gov_state.empty:
        gov_state.to_csv("2026/US_Governor_state_results.csv", index=False)

    house_df = scrape_house(
        states=None,
        force_refresh=args.force_refresh,
        min_delay=args.delay_min,
        max_delay=args.delay_max,
    )
    if not house_df.empty:
        house_df.to_csv("2026/US_House_results.csv", index=False)

    print("\nAll 2026 Senate, Governor, and House CSVs updated.")


if __name__ == "__main__":
    main()
