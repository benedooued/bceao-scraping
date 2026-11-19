import os
import re
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict, Union
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ==========================================================
# CONFIGURATION & CONSTANTS
# ==========================================================

BASE_URL: str = "https://edenpub.bceao.int/"
HOME_URL: str = urljoin(BASE_URL, "rapportPredefini.php")

OUTPUT_DIR: Path = Path("exports")
OUTPUT_DIR.mkdir(exist_ok=True)

# List of default country codes used if detection fails
KNOWN_COUNTRIES: List[str] = ["B", "C", "A", "S", "D", "H", "K", "T", "Z"]

# Annual time range settings
ANNUAL_START_YEAR: int = 1960
ANNUAL_END_YEAR: int = 2026

# Monthly time range settings: (Month, Year)
MONTHLY_START: Tuple[str, int] = ("01", 2020)  # January 2020
MONTHLY_END: Tuple[str, int] = ("12", 2025)    # December 2025

METADATA: str = "1"
VERIFY_SSL: bool = False

warnings.filterwarnings("ignore", category=InsecureRequestWarning)


# ==========================================================
# CUSTOM TYPES
# ==========================================================

class ReportDict(TypedDict):
    """Structure representing extracted report metadata."""
    frequency: str
    id_tab: str
    title: str


PayloadType = List[Tuple[str, str]]


# ==========================================================
# HTTP SESSION MANAGEMENT
# ==========================================================

def create_session() -> requests.Session:
    """Creates and configures a requests Session with a default User-Agent.

    Returns:
        requests.Session: Configured session instance.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    })
    return session


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs
) -> requests.Response:
    """Executes an HTTP request with automatic retry logic (up to 3 attempts).

    Args:
        session (requests.Session): Active HTTP session.
        method (str): HTTP method ('GET', 'POST', etc.).
        url (str): Target URL for the request.
        **kwargs: Additional parameters passed to `requests.Session.request`.

    Raises:
        requests.RequestException: If all 3 request attempts fail.

    Returns:
        requests.Response: Successful HTTP response object.
    """
    for attempt in range(3):
        try:
            response = session.request(
                method,
                url,
                timeout=(15, 180),
                verify=VERIFY_SSL,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            print(f"  Tentative {attempt + 1}/3 échouée : {error}")
            if attempt == 2:
                raise
            time.sleep(5)


# ==========================================================
# 1. REPORT EXTRACTION
# ==========================================================

def get_homepage(session: requests.Session) -> BeautifulSoup:
    """Fetches and parses the main homepage.

    Args:
        session (requests.Session): Active HTTP session.

    Returns:
        BeautifulSoup: Parsed HTML tree of the homepage.
    """
    response = request_with_retry(session, "GET", HOME_URL)
    return BeautifulSoup(response.text, "html.parser")


def extract_reports(homepage: BeautifulSoup) -> List[ReportDict]:
    """Parses `onclick` JavaScript calls on the homepage to find available reports.

    Args:
        homepage (BeautifulSoup): Parsed HTML of the homepage.

    Returns:
        List[ReportDict]: List of extracted reports containing `frequency`, `id_tab`, and `title`.
    """
    reports: List[ReportDict] = []
    seen: set = set()

    # Regex capturing arguments from soumettreTab('freq', 'id', 'title')
    pattern = re.compile(
        r"""soumettreTab\(\s*['"]([^'"]+)['"]\s*,\s*
        ['"]([^'"]+)['"]\s*,\s*['"]((?:\\.|[^'"])*)['"]""",
        re.VERBOSE
    )

    for element in homepage.find_all(True):
        onclick: str = element.get("onclick", "")
        match = pattern.search(onclick)

        if not match:
            continue

        frequency, report_id, title = match.groups()

        if report_id in seen:
            continue

        seen.add(report_id)

        reports.append({
            "frequency": frequency.strip(),
            "id_tab": report_id.strip(),
            "title": title.replace("\\'", "'").strip()
        })

    return reports


# ==========================================================
# 2. REPORT CONFIGURATION
# ==========================================================

def open_report(session: requests.Session, report: ReportDict) -> BeautifulSoup:
    """Posts a request to load the configuration form for a given report.

    Args:
        session (requests.Session): Active HTTP session.
        report (ReportDict): Dictionary containing report details.

    Returns:
        BeautifulSoup: Parsed HTML of the report configuration page.
    """
    url = urljoin(BASE_URL, "tableauPredefini.php")
    payload = {
        "frequence": report["frequency"],
        "idTab": report["id_tab"],
        "libelleTab": report["title"]
    }

    response = request_with_retry(
        session,
        "POST",
        url,
        data=payload,
        headers={"Referer": HOME_URL}
    )

    return BeautifulSoup(response.text, "html.parser")


# ==========================================================
# 3. COUNTRY DETECTION
# ==========================================================

def detect_countries(form: Tag) -> List[str]:
    """Detects available country checkbox values inside the report form.

    Args:
        form (Tag): BeautifulSoup Tag object corresponding to the form.

    Returns:
        List[str]: List of country code strings. Falls back to `KNOWN_COUNTRIES` if none found.
    """
    countries: List[str] = []

    for checkbox in form.find_all("input", {"type": "checkbox"}):
        value = checkbox.get("value")
        if value and value.strip():
            countries.append(value.strip())

    # Remove duplicates preserving order
    countries = list(dict.fromkeys(countries))

    if not countries:
        countries = KNOWN_COUNTRIES.copy()

    return countries


# ==========================================================
# 4. PARAMETER BUILDING
# ==========================================================

def build_params(frequency: str, countries: List[str]) -> str:
    """Formats payload configuration string based on frequency and country list.

    Args:
        frequency (str): Report frequency ('M' for monthly, 'A' for annual).
        countries (List[str]): List of target country codes.

    Raises:
        ValueError: If an unsupported frequency code is passed.

    Returns:
        str: Formatted parameter string formatted for backend processing.
    """
    country_string: str = ";".join(countries)

    if frequency == "M":
        start_month, start_year = MONTHLY_START
        end_month, end_year = MONTHLY_END
        date_start = f"{start_month};{start_year}"
        date_end = f"{end_month};{end_year}"

    elif frequency == "A":
        date_start = str(ANNUAL_START_YEAR)
        date_end = str(ANNUAL_END_YEAR)

    else:
        raise ValueError(f"Fréquence non prise en charge : {frequency}")

    return f"{frequency}*{country_string}*{date_start}*{date_end}*{METADATA}*l"


# ==========================================================
# 5. FORM SERIALIZATION & PAYLOAD MODIFICATION
# ==========================================================

def serialize_form(form: Tag, countries: Optional[List[str]] = None) -> PayloadType:
    """Extracts key-value tuple pairs from form inputs.

    Args:
        form (Tag): HTML form tag to extract inputs from.
        countries (Optional[List[str]], optional): Selected checkboxes to filter by. Defaults to None.

    Returns:
        PayloadType: List of (name, value) tuples suitable for POST encoding.
    """
    countries = countries or []
    payload: PayloadType = []

    for element in form.find_all(["input", "select", "textarea"]):
        name: Optional[str] = element.get("name")
        if not name:
            continue

        tag: str = element.name
        input_type: str = element.get("type", "").lower()

        if tag == "input":
            if input_type in ["submit", "button", "reset", "image"]:
                continue

            value: str = element.get("value", "")

            if input_type == "checkbox":
                if value not in countries:
                    continue
            elif input_type == "radio":
                if not element.has_attr("checked"):
                    continue

        elif tag == "select":
            selected = element.find("option", selected=True)
            if selected is None:
                selected = element.find("option")
            if selected is None:
                continue
            value = selected.get("value", selected.text.strip())
        else:
            value = element.text

        payload.append((name, value))

    return payload


def set_payload_value(payload: PayloadType, key: str, value: str) -> PayloadType:
    """Updates or appends a key-value pair in a list of tuples payload.

    Args:
        payload (PayloadType): Original list of (name, value) tuples.
        key (str): Field name to set or update.
        value (str): Value assigned to key.

    Returns:
        PayloadType: New updated payload tuple list.
    """
    updated_payload: PayloadType = [
        (name, val) for name, val in payload if name != key
    ]
    updated_payload.append((key, value))
    return updated_payload


# ==========================================================
# 6. REPORT GENERATION
# ==========================================================

def generate_report(
    session: requests.Session,
    report: ReportDict,
    report_page: BeautifulSoup,
    countries: List[str],
    params: str
) -> BeautifulSoup:
    """Submits form to generate full HTML report.

    Args:
        session (requests.Session): Active HTTP session.
        report (ReportDict): Metadata dictionary of target report.
        report_page (BeautifulSoup): BeautifulSoup object of setup page.
        countries (List[str]): List of target country codes.
        params (str): Built parameter payload string.

    Raises:
        ValueError: If `#form_consultation` is not located on page.

    Returns:
        BeautifulSoup: Generated result report HTML.
    """
    form: Optional[Tag] = report_page.find("form", id="form_consultation")

    if form is None:
        raise ValueError("Formulaire form_consultation introuvable.")

    action: str = form.get("action") or "rapportPredefini.php"
    url: str = urljoin(BASE_URL, action)

    payload: PayloadType = serialize_form(form, countries)
    payload = set_payload_value(payload, "params", params)
    payload = set_payload_value(payload, "idTab", report["id_tab"])

    response = request_with_retry(
        session,
        "POST",
        url,
        data=payload,
        headers={"Referer": url}
    )

    return BeautifulSoup(response.text, "html.parser")


# ==========================================================
# 7. EXPORT DOWNLOAD
# ==========================================================

def download_report(
    session: requests.Session,
    report: ReportDict,
    result_page: BeautifulSoup,
    params: str
) -> Path:
    """Requests and downloads report file content (.xlsx, .xls, or .csv).

    Args:
        session (requests.Session): Active HTTP session.
        report (ReportDict): Target report details dictionary.
        result_page (BeautifulSoup): Parsed HTML response of generated report.
        params (str): Built parameter string.

    Raises:
        ValueError: If server returns HTML content instead of downloadable file.

    Returns:
        Path: Local path to written output file.
    """
    export_form: Optional[Tag] = None

    for form in result_page.find_all("form"):
        action: str = form.get("action", "").lower()
        if "export" in action:
            export_form = form
            break

    if export_form is not None:
        action = export_form.get("action", "")
        export_url = urljoin(BASE_URL, action)
        payload = serialize_form(export_form)
    else:
        export_url = urljoin(BASE_URL, "exportTableauPredefiniEnColonne.php")
        payload = []

    payload = set_payload_value(payload, "params", params)
    payload = set_payload_value(payload, "idTab", report["id_tab"])
    payload = set_payload_value(payload, "export", "")

    response = request_with_retry(
        session,
        "POST",
        export_url,
        data=payload,
        headers={"Referer": HOME_URL}
    )

    content_type: str = response.headers.get("Content-Type", "").lower()
    if "html" in content_type:
        raise ValueError("Le serveur a renvoyé une page HTML au lieu du fichier.")

    # File magic-bytes detection
    if response.content.startswith(b"PK"):
        extension = ".xlsx"
    elif response.content.startswith(bytes.fromhex("D0CF11E0")):
        extension = ".xls"
    else:
        extension = ".csv"

    safe_title: str = re.sub(r'[<>:"/\\|?*]+', "_", report["title"])
    filename: str = f"{report['id_tab']}_{safe_title}{extension}"
    filepath: Path = OUTPUT_DIR / filename

    filepath.write_bytes(response.content)
    return filepath


# ==========================================================
# 8. MAIN EXECUTION PIPELINE
# ==========================================================

def main() -> None:
    """Executes scraping pipeline to fetch, generate, and download all reports."""
    session: requests.Session = create_session()

    print("\nConnexion au site BCEAO...")
    homepage: BeautifulSoup = get_homepage(session)
    reports: List[ReportDict] = extract_reports(homepage)

    print(f"\nNombre de rapports détectés : {len(reports)}")

    if not reports:
        print("Aucun rapport détecté. Vérifie la page d'accueil.")
        return

    successful: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []

    for index, report in enumerate(reports, start=1):
        print("\n" + "=" * 65)
        print(f"Rapport {index}/{len(reports)}")
        print(report["title"])
        print("Identifiant :", report["id_tab"])
        print("Fréquence :", report["frequency"])

        try:
            report_page: BeautifulSoup = open_report(session, report)
            form: Optional[Tag] = report_page.find("form", id="form_consultation")

            if form is None:
                raise ValueError("Formulaire de configuration introuvable.")

            countries: List[str] = detect_countries(form)
            print("Pays détectés :", countries)

            params: str = build_params(report["frequency"], countries)
            print("Paramètres :", params)

            result_page: BeautifulSoup = generate_report(
                session, report, report_page, countries, params
            )

            filepath: Path = download_report(session, report, result_page, params)
            print("Export réussi :", filepath)

            successful.append({
                "id": report["id_tab"],
                "title": report["title"],
                "frequency": report["frequency"],
                "file": str(filepath)
            })

        except Exception as error:
            print("ERREUR :", error)
            failed.append({
                "id": report["id_tab"],
                "title": report["title"],
                "error": str(error)
            })

        time.sleep(2)

    pd.DataFrame(successful).to_csv(
        OUTPUT_DIR / "successful_exports.csv",
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(failed).to_csv(
        OUTPUT_DIR / "failed_exports.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 65)
    print("EXTRACTION TERMINÉE")
    print("=" * 65)
    print("Rapports détectés :", len(reports))
    print("Exports réussis :", len(successful))
    print("Exports échoués :", len(failed))
    print("\nRésultats disponibles dans :", OUTPUT_DIR.resolve())


if __name__ == "__main__":
    main()