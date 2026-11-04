# election_analysis

Hobby tools for scraping and analyzing U.S. election results.

## Directory Structure

- `common/`: Shared schemas, polite caching HTTP fetcher, and universal multi-year plotting functions.
- `2022/`: 2022 midterm scraping (Reuters) and analysis notebook.
- `2024/`: 2024 general election scraping (NPR) for Presidential and House races.
- `2026/`: 2026 midterm election scraping (NBC News) and analysis for U.S. Senate, U.S. House, and Gubernatorial races.

---

## Canonical Data Format (Year-Agnostic)

All scrapers now produce standardized CSV schemas defined in `common/schemas.py`:

### 1. County-Level & Statewide Schemas (`US_Senate_county_results.csv`, `US_Governor_county_results.csv`, `US_*_state_results.csv`)
Independent of candidate names so the same analysis code runs every cycle:
```csv
Year,Office,State,County,Percent Reporting,Total Votes,Dem Candidate,Dem Votes,Dem Pct,GOP Candidate,GOP Votes,GOP Pct,Other Votes,Other Pct,Winner,Winner Party,Updated
```

### 2. District-Level Schema (`US_House_results.csv`)
Standardized district and candidate breakdown:
```csv
Year,Office,State,District,Candidate,Party,Percentage of Votes (%),Total Votes,Incumbent,Percent Reporting,Winner,Updated
```

---

## Rate Limiting & Polite Scraping (`common/fetcher.py`)

All network requests go through `PoliteFetcher` to protect against rate limits and IP blocking:
- **Disk Caching**: Responses are cached locally in `.cache/` (default TTL: 30 minutes). If data is already cached and fresh, **zero network calls are made**.
- **Randomized Jitter Delays**: Enforces a polite 2.0 to 4.5 second delay between live requests to mimic organic human browsing.
- **Stealth Headers**: Full browser headers (`User-Agent`, `Sec-Fetch-*`, `Accept-Language`, etc.).
- **Automatic Backoff**: Retries with exponential backoff on HTTP 429 (Too Many Requests).

---

## Running the 2026 Midterm Tools

### Senate Results Scraper
```bash
# Scrape key battlegrounds (uses local cache if available; polite delays if fetching)
./.venv/bin/python 2026/US_Senate_results.py --battlegrounds

# Scrape all 35 Senate contests
./.venv/bin/python 2026/US_Senate_results.py --all

# Force a fresh download bypassing cache
./.venv/bin/python 2026/US_Senate_results.py --states Alabama --force-refresh
```

### House Results Scraper
```bash
# Scrape House battleground states
./.venv/bin/python 2026/US_House_results.py --battlegrounds

# Scrape all 435 congressional districts nationwide
./.venv/bin/python 2026/US_House_results.py --all
```

### Governor Results Scraper
```bash
# Scrape Governor battleground states
./.venv/bin/python 2026/US_Governor_results.py --battlegrounds

# Scrape all 36 gubernatorial contests nationwide
./.venv/bin/python 2026/US_Governor_results.py --all
```

### Universal Plotting & Projections (`common/plots.py`)
```bash
# Senate Balance of Power, Statewide Margins & Turnout Projections
./.venv/bin/python 2026/plot_senate.py

# Governor Balance of Power, Statewide Margins, Turnout & Governor-vs-Senate Ticket Splitting
./.venv/bin/python 2026/plot_governor.py

# House Seats Won / Leading by Party, Popular Vote & Votes per Seat
./.venv/bin/python 2026/plot_house.py

# 5 Multi-Panel Deep-Dive Diagnostic Plots
./.venv/bin/python 2026/plot_deep_dive.py
```

### Interactive Jupyter Notebook
Open `2026/2026_midterm_analysis.ipynb` to explore the standardized datasets interactively.
