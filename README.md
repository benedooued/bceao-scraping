# BCEAO Economic Data Scraper

## Overview

This project is an automated web scraping tool designed to extract and download statistical reports from the **Central Bank of West African States (BCEAO)** public data portal.

Instead of manually selecting reports, countries, and time periods, the script automatically discovers available reports, configures the extraction parameters, and downloads the corresponding datasets.

The extracted data can subsequently be used for data analysis, statistical studies, economic research, and business intelligence dashboards.

## Features

- **Automatic Report Discovery:** Detects all available predefined reports from the BCEAO portal.
- **Dynamic Country Detection:** Identifies available countries directly from report configuration forms.
- **Multi-Country Extraction:** Retrieves data for all detected countries in a single extraction process.
- **Historical Data Collection:** Supports annual and monthly reports with configurable date ranges.
- **Automated Downloads:** Downloads reports in their original Excel or CSV format.
- **Error Handling:** Implements HTTP request retries and handles individual report extraction failures.
- **Extraction Logging:** Generates CSV files summarizing successful and failed exports.

## Technologies Used

- Python
- Requests – HTTP requests and session management.
- BeautifulSoup – HTML parsing and report discovery.
- Pandas – Data management and extraction summaries.
- Regular Expressions – Dynamic extraction of report metadata.

## Project Structure

```text
bceao-data-scraper/
│
├── main.py
├── exports/
│   ├── successful_exports.csv
│   ├── failed_exports.csv
│   └── ...
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/USERNAME/bceao-data-scraper.git

cd bceao-data-scraper
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install requests pandas beautifulsoup4
```

Alternatively, install dependencies from the requirements file:

```bash
pip install -r requirements.txt
```

## Configuration

The extraction parameters can be modified directly in the configuration section of `main.py`.

| Parameter | Description | Default |
|---|---|---|
| `ANNUAL_START_YEAR` | Starting year for annual reports | 1960 |
| `ANNUAL_END_YEAR` | Ending year for annual reports | 2026 |
| `MONTHLY_START` | Starting month and year | January 2020 |
| `MONTHLY_END` | Ending month and year | December 2025 |
| `KNOWN_COUNTRIES` | Fallback country codes | B, C, A, S, D, H, K, T, Z |
| `VERIFY_SSL` | SSL certificate verification | False |

The script automatically detects available country codes from each report's configuration form. The predefined country list is used as a fallback.

## Usage

Run the extraction script:

```bash
python main.py
```

The script performs the following operations:

1. Connects to the BCEAO data portal.
2. Retrieves the list of available statistical reports.
3. Opens each report's configuration page.
4. Detects the available countries.
5. Builds extraction parameters based on report frequency.
6. Generates the requested statistical report.
7. Downloads the resulting dataset.
8. Records successful and failed extractions.

## Output

All downloaded datasets are stored in the `exports/` directory.

The script also generates two summary files:

**`successful_exports.csv`**

Contains information about successfully downloaded reports:

- Report ID
- Report title
- Report frequency
- Exported file path

**`failed_exports.csv`**

Contains information about reports that could not be extracted:

- Report ID
- Report title
- Error description

The downloaded files retain their original format whenever possible (XLSX, XLS, or CSV).

## Error Handling

The extraction process includes:

- Up to three HTTP request attempts.
- A five-second delay between failed attempts.
- A two-second pause between report extractions.
- Individual error tracking to allow the extraction process to continue when a report fails.


## Author

**Wende Benedo Ariel OUEDRAOGO**

Data Scientist | Machine Learning & AI

[GitHub](https://github.com/USERNAME) | [LinkedIn](https://www.linkedin.com/)
