
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin
import urllib3
from collections import Counter

# Désactivation temporaire des avertissements SSL
# À corriger avant une utilisation en production.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://edenpub.bceao.int"
HOME_URL = f"{BASE_URL}/rapportPredefini.php"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": HOME_URL
})


# 1. Connexion au site
def get_homepage():
    response = session.get(
        HOME_URL,
        timeout=30,
        verify=False
    )
    response.raise_for_status()

    print("Homepage:", response.status_code)

    return BeautifulSoup(response.text, "html.parser")


# 2. Extraction des rapports
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


# 3. Ouverture du rapport
def open_report(report):
    payload = {
        "frequence": report["frequency"],
        "idTab": report["id_tab"],
        "libelleTab": report["title"]
    }

    response = session.post(
        f"{BASE_URL}/tableauPredefini.php",
        data=payload,
        headers={"Referer": HOME_URL},
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    print("Report selection:", response.status_code)

    return BeautifulSoup(response.text, "html.parser")


# 4. Génération du rapport
def generate_report(soup, report):
    form = soup.find("form", id="form_consultation")

    if not form:
        print("Consultation form not found!")
        return None

    action_url = urljoin(
        f"{BASE_URL}/tableauPredefini.php",
        form.get("action")
    )

    # Pays
    countries = ["B", "C", "A", "S", "D", "H", "K", "T", "Z"]

    frequency = report["frequency"]

    # Test mensuel : janvier 2020 à décembre 2025
    start_month, start_year = "1", "2020"
    end_month, end_year = "12", "2025"

    params = (
        f"{frequency}*"
        f"{';'.join(countries)}*"
        f"{start_month};{start_year}*"
        f"{end_month};{end_year}*1*l"
    )

    payload = {
        "idTab": report["id_tab"],
        "frequence": frequency,
        "params": params,
        "metadonnee": "1",
        "mois_debut": start_month,
        "annee_debut": start_year,
        "mois_fin": end_month,
        "annee_fin": end_year
    }

    for country in countries:
        payload[country] = country

    response = session.post(
        action_url,
        data=payload,
        headers={
            "Referer": f"{BASE_URL}/tableauPredefini.php"
        },
        timeout=60,
        verify=False
    )

    response.raise_for_status()

    print("Report generation:", response.status_code)
    print("Final URL:", response.url)

    return response


# 5. Extraction du tableau
def extract_data(response):
    soup = BeautifulSoup(response.text, "html.parser")

    expected_headers = [
        "CODE",
        "LIBELLE",
        "UNITE DE MESURE",
        "MAGNITUDE",
        "SOURCE",
        "TYPE SERIE",
        "METHODE OBSERVATION"
    ]

    for index, table in enumerate(soup.find_all("table")):

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)

            headers = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if headers[:7] == expected_headers:

                data = []

                for data_row in table.find_all("tr"):
                    values = [
                        cell.get_text(" ", strip=True)
                        for cell in data_row.find_all(
                            ["th", "td"],
                            recursive=False
                        )
                    ]

                    if len(values) == len(headers) and values != headers:
                        data.append(values)

                df = pd.DataFrame(data, columns=headers)

                print("Data table:", index)
                print("DataFrame shape:", df.shape)

                return df

    print("Structured data table not found.")
    return None


# 6. MAIN
if __name__ == "__main__":

    homepage = get_homepage()

    reports = extract_reports(homepage)

    print("Total reports:", len(reports))

    # Deuxième rapport : IHPC mensuel
    report = next(
        (
            r for r in reports
            if "PIB ET SES EMPLOIS A PRIX CONSTANT" in r["title"]
        ),
        None
    )
    # report = next(
    #     (
    #         r for r in reports
    #         if "INDICE DES PRIX A LA CONSOMMATION MENSUEL" in r["title"]
    #     ),
    #     None
    # )

    if report is None:
        print("Monthly report not found.")
        raise SystemExit

    print("\nTesting:", report["title"])
    print("Frequency:", report["frequency"])
    print("ID:", report["id_tab"])

    report_soup = open_report(report)

    response = generate_report(report_soup, report)
    
    print(Counter(report["frequency"] for report in reports))

    if response:
        df = extract_data(response)

        if df is not None:
            df.to_csv(
                "bceao_ihpc_mensuel.csv",
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

            print("CSV exported successfully!")
            print(df.head())
            print(df.columns.tolist())
            print(df.shape)
            print(df.isna().sum())
            print(df.head(10))
