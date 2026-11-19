import re
from typing import List, Optional, Tuple, TypedDict
from bs4 import BeautifulSoup, Tag
from config import ANNUAL_END_YEAR, ANNUAL_START_YEAR, KNOWN_COUNTRIES, METADATA, MONTHLY_END, MONTHLY_START


class ReportDict(TypedDict):
    """Structure representing extracted report metadata."""
    frequency: str
    id_tab: str
    title: str


PayloadType = List[Tuple[str, str]]

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
