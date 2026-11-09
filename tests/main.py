
import requests
from bs4 import BeautifulSoup
from config import COUNTRIES, HOME_URL

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


if __name__ == "__main__":
    soup = get_homepage()

    print("\nHomepage retrieved successfully.")
