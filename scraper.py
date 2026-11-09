
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from config import HOME_URL, BASE_URL


import os


def download_report_excel(session, report, params):
    export_url = urljoin(
        BASE_URL + "/",
        "exportTableauPredefiniEnColonne.php"
    )

    payload = {
        "params": params,
        "export": "",
        "idTab": report["id_tab"]
    }

    response = session.post(
        export_url,
        data=payload,
        headers={"Referer": HOME_URL},
        timeout=(15, 180),
        verify=False
    )

    response.raise_for_status()

    os.makedirs("exports", exist_ok=True)

    filename = f"report_{report['id_tab']}.xls"
    filepath = os.path.join("exports", filename)

    with open(filepath, "wb") as file:
        file.write(response.content)

    print(f"Export téléchargé : {filepath}")
    print(f"Taille : {len(response.content)} octets")
    print(f"Content-Type : {response.headers.get('Content-Type')}")

    return filepath


def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": HOME_URL
    })

    return session


def get_homepage(session):
    response = session.get(
        HOME_URL,
        timeout=(15, 120),
        verify=False
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    return soup


def extract_reports(soup):
    reports = []

    links = soup.select("ul.extend a[onclick]")

    for link in links:
        onclick = link.get("onclick", "")

        match = re.search(
            r"soumettreTab\('([^']+)','([^']+)','(.*?)'\)",
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







def open_report(session, report):
    url = urljoin(HOME_URL, "tableauPredefini.php")

    payload = {
        "frequence": report["frequency"],
        "idTab": report["id_tab"],
        "libelleTab": report["title"]
    }

    response = session.post(
        url,
        data=payload,
        headers={"Referer": HOME_URL},
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    return soup



def inspect_report_form(soup):
    form = soup.find("form", id="form_consultation")

    if not form:
        raise ValueError("Consultation form not found")

    countries = [
        checkbox.get("value")
        for checkbox in form.find_all("input", type="checkbox")
        if checkbox.get("value")
    ]

    years = {}
    months = {}

    for name in ["annee_debut", "annee_fin"]:
        select = form.find("select", {"name": name})
        if select:
            years[name] = [
                option.get("value")
                for option in select.find_all("option")
                if option.get("value")
            ]

    for name in ["mois_debut", "mois_fin"]:
        select = form.find("select", {"name": name})
        if select:
            months[name] = [
                option.get("value")
                for option in select.find_all("option")
                if option.get("value")
            ]

    return {
        "countries": countries,
        "years": years,
        "months": months
    }
    
def generate_report(session, report, payload):
    url = f"{BASE_URL}/rapportPredefini.php"

    response = session.post(
        url,
        data=payload,
        headers={"Referer": f"{BASE_URL}/tableauPredefini.php"},
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    return soup




