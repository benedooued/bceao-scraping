
import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://edenpub.bceao.int"
HOME_URL = f"{BASE_URL}/rapportPredefini.php"

# Maintain cookies and session information
session = requests.Session()

# Browser-like headers
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": HOME_URL
})






def get_homepage():
    response = session.get(
        HOME_URL,
        timeout=30,
        verify=False  # Diagnostic only
    )

    response.raise_for_status()

    print("Status:", response.status_code)
    print("Cookies:", session.cookies.get_dict())

    soup = BeautifulSoup(response.text, "html.parser")

    print("Title:", soup.title.get_text(strip=True)
          if soup.title else "No title")

    return soup

def extract_reports(soup):
    reports = []

    for link in soup.select("ul.extend a[onclick]"):
        onclick = link.get("onclick", "")

        match = re.search(
            r"soumettreTab\('([^']+)','([^']+)','([^']+)'\)",
            onclick
        )

        if match:
            frequency, id_tab, title = match.groups()

            reports.append({
                "frequency": frequency,
                "id_tab": id_tab,
                "title": title.strip()
            })

    return reports



if __name__ == "__main__":
    soup = get_homepage()

    reports = extract_reports(soup)

    print(f"\nTotal reports found: {len(reports)}")

    for report in reports:
        print(report)