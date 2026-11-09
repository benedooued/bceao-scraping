
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

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



def inspect_forms(soup):
    for i, form in enumerate(soup.find_all("form")):
        print(f"\nFORM {i}")
        print("Name:", form.get("name"))
        print("ID:", form.get("id"))
        print("Action:", form.get("action"))
        print("Method:", form.get("method"))

        for field in form.find_all(["input", "select"]):
            print({
                "tag": field.name,
                "name": field.get("name"),
                "type": field.get("type"),
                "value": field.get("value")
            })






def open_report(report):
    url = urljoin(BASE_URL, "tableauPredefini.php")

    payload = {
        "frequence": report["frequency"],
        "idTab": report["id_tab"],
        "libelleTab": report["title"]
    }

    response = session.post(
        url,
        data=payload,
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    print("\nReport selection submitted.")
    print("Status:", response.status_code)
    print("URL:", response.url)

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the consultation form
    form = soup.find("form", id="form_consultation")

    if not form:
        print("Consultation form not found!")
        print("Page title:", soup.title.get_text(strip=True)
              if soup.title else "No title")
        return None

    print("\nConsultation form found!")

    print("\nAll form inputs:")
    for field in form.find_all(["input", "select"]):
        print({
        "tag": field.name,
        "name": field.get("name"),
        "type": field.get("type"),
        "value": field.get("value"),
        "checked": field.has_attr("checked")
        })
        
    print("\nSelect fields:")
    for select in form.find_all("select"):
        print("\nName:", select.get("name"))

        options = [
            (option.get("value"), option.get_text(strip=True))
            for option in select.find_all("option")
        ]

        print("Options:", options[:5], "...", options[-3:])
        
        
    # Inspect year options
    for name in ["annee_debut", "annee_fin"]:
        select = form.find("select", attrs={"name": name})

        if select:
            options = [
                (o.get("value"), o.get_text(strip=True))
                for o in select.find_all("option")
            ]

            print(f"\n{name}:")
            print("First options:", options[:3])
            print("Last options:", options[-3:])

    print("\nForm action:", form.get("action"))
    print("Form method:", form.get("method"))

    return soup





def generate_report(soup):
    form = soup.find("form", id="form_consultation")

    # Identify the form destination
    action_url = urljoin(
        "https://edenpub.bceao.int/tableauPredefini.php",
        form.get("action")
    )

    # Select all countries
    countries = ["B", "C", "A", "S", "D", "H", "K", "T", "Z"]

    payload = {
        "idTab": "5",
        "frequence": "A",
        "annee_debut": "1960",
        "annee_fin": "2026",
        "metadonnee": "1",
        "params": ""
    }

    # Add country checkboxes to the payload
    for country in countries:
        payload[country] = country

    response = session.post(
        action_url,
        data=payload,
        headers={"Referer": "https://edenpub.bceao.int/tableauPredefini.php"},
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    print("\nReport generated!")
    print("Status:", response.status_code)
    print("URL:", response.url)
    print("Content type:", response.headers.get("Content-Type"))

    return response


if __name__ == "__main__":
    homepage = get_homepage()

    reports = extract_reports(homepage)
    

    # print("Total reports:", len(reports))

    first_report = reports[0]
    report_page = open_report(first_report)

    if report_page:
        result = generate_report(report_page)

    # print("\nTesting:", first_report["title"])

    # report_page = open_report(first_report)