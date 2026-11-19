import os
import re
import time
import warnings
from pathlib import Path
from urllib.parse import urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning


# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_URL = "https://edenpub.bceao.int/"
HOME_URL = urljoin(BASE_URL, "rapportPredefini.php")

OUTPUT_DIR = Path("exports")
OUTPUT_DIR.mkdir(exist_ok=True)

# Pays : les codes seront aussi détectés depuis le formulaire.
KNOWN_COUNTRIES = ["B", "C", "A", "S", "D", "H", "K", "T", "Z"]

# Période annuelle
ANNUAL_START_YEAR = 1960
ANNUAL_END_YEAR = 2026

# Période mensuelle
MONTHLY_START = ("01", 2020)  # Janvier 2020
MONTHLY_END = ("12", 2025)    # Décembre 2025

METADATA = "1"

# Le site a précédemment fonctionné avec verify=False.
# À réactiver à True lorsque le problème de certificat SSL sera réglé.
VERIFY_SSL = False

warnings.filterwarnings("ignore", category=InsecureRequestWarning)


# ==========================================================
# SESSION HTTP
# ==========================================================

def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    })

    return session


def request_with_retry(session, method, url, **kwargs):

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

            print(
                f"  Tentative {attempt + 1}/3 échouée : {error}"
            )

            if attempt == 2:
                raise

            time.sleep(5)


# ==========================================================
# 1. RECUPERER TOUS LES RAPPORTS
# ==========================================================

def get_homepage(session):

    response = request_with_retry(
        session,
        "GET",
        HOME_URL
    )

    return BeautifulSoup(response.text, "html.parser")


def extract_reports(homepage):

    reports = []
    seen = set()

    # Captures argument of the soumettreTab function in the onclick attribute
    pattern = re.compile(
        r"""soumettreTab\(\s*['"]([^'"]+)['"]\s*,\s*
        ['"]([^'"]+)['"]\s*,\s*['"]((?:\\.|[^'"])*)['"]""",
        re.VERBOSE
    )

    for element in homepage.find_all(True):

        onclick = element.get("onclick", "")

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
# 2. OUVRIR LA CONFIGURATION D'UN RAPPORT
# ==========================================================

def open_report(session, report):

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
# 3. DETECTER LES PAYS DISPONIBLES
# ==========================================================

def detect_countries(form):

    countries = []

    for checkbox in form.find_all(
        "input",
        {"type": "checkbox"}
    ):

        value = checkbox.get("value")

        if value and value.strip():
            countries.append(value.strip())

    # Éliminer les doublons
    countries = list(dict.fromkeys(countries))

    # Si le formulaire ne permet pas de détecter les cases,
    # utiliser les codes déjà identifiés.
    if not countries:
        countries = KNOWN_COUNTRIES.copy()

    return countries


# ==========================================================
# 4. CONSTRUIRE LES PARAMETRES DU RAPPORT
# ==========================================================

def build_params(frequency, countries):

    country_string = ";".join(countries)

    if frequency == "M":

        start_month, start_year = MONTHLY_START
        end_month, end_year = MONTHLY_END

        date_start = f"{start_month};{start_year}"
        date_end = f"{end_month};{end_year}"

    elif frequency == "A":

        date_start = str(ANNUAL_START_YEAR)
        date_end = str(ANNUAL_END_YEAR)

    else:

        raise ValueError(
            f"Fréquence non prise en charge : {frequency}"
        )

    return (
        f"{frequency}*"
        f"{country_string}*"
        f"{date_start}*"
        f"{date_end}*"
        f"{METADATA}*l"
    )


# ==========================================================
# 5. CONSTRUIRE LE PAYLOAD D'UN FORMULAIRE HTML
# ==========================================================

def serialize_form(form, countries=None):


    countries = countries or []

    payload = []

    for element in form.find_all(["input", "select", "textarea"]):

        name = element.get("name")

        if not name:
            continue

        tag = element.name
        input_type = element.get("type", "").lower()

        if tag == "input":

            if input_type in ["submit", "button", "reset", "image"]:
                continue

            value = element.get("value", "")

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


def set_payload_value(payload, key, value):

    payload = [
        (name, val)
        for name, val in payload
        if name != key
    ]

    payload.append((key, value))

    return payload


# ==========================================================
# 6. GENERER LE RAPPORT
# ==========================================================

def generate_report(session, report, report_page, countries, params):

    form = report_page.find(
        "form",
        id="form_consultation"
    )

    if form is None:

        raise ValueError(
            "Formulaire form_consultation introuvable."
        )

    action = form.get("action") or "rapportPredefini.php"
    url = urljoin(BASE_URL, action)

    payload = serialize_form(form, countries)

    payload = set_payload_value(
        payload,
        "params",
        params
    )

    payload = set_payload_value(
        payload,
        "idTab",
        report["id_tab"]
    )

    response = request_with_retry(
        session,
        "POST",
        url,
        data=payload,
        headers={"Referer": url}
    )

    return BeautifulSoup(response.text, "html.parser")


# ==========================================================
# 7. TELECHARGER L'EXPORT
# ==========================================================

def download_report(session, report, result_page, params):

    export_form = None

    for form in result_page.find_all("form"):

        action = form.get("action", "").lower()

        if "export" in action:
            export_form = form
            break

    if export_form is not None:

        action = export_form.get("action")
        export_url = urljoin(BASE_URL, action)

        payload = serialize_form(export_form)

    else:

        # URL de secours si le formulaire d'export
        # n'est pas présent dans le résultat HTML.
        export_url = urljoin(
            BASE_URL,
            "exportTableauPredefiniEnColonne.php"
        )

        payload = []

    payload = set_payload_value(
        payload,
        "params",
        params
    )

    payload = set_payload_value(
        payload,
        "idTab",
        report["id_tab"]
    )

    payload = set_payload_value(
        payload,
        "export",
        ""
    )

    response = request_with_retry(
        session,
        "POST",
        export_url,
        data=payload,
        headers={"Referer": HOME_URL}
    )

    # Vérifier que le serveur a renvoyé un fichier
    content_type = response.headers.get("Content-Type", "").lower()

    if "html" in content_type:

        raise ValueError(
            "Le serveur a renvoyé une page HTML au lieu du fichier."
        )

    # Déterminer le format réel du fichier
    if response.content.startswith(b"PK"):
        extension = ".xlsx"

    elif response.content.startswith(bytes.fromhex("D0CF11E0")):
        extension = ".xls"

    else:
        extension = ".csv"

    safe_title = re.sub(
        r'[<>:"/\\|?*]+',
        "_",
        report["title"]
    )

    filename = (
        f"{report['id_tab']}_{safe_title}"
        f"{extension}"
    )

    filepath = OUTPUT_DIR / filename

    filepath.write_bytes(response.content)

    return filepath


# ==========================================================
# 8. EXECUTION COMPLETE
# ==========================================================

def main():

    session = create_session()

    print("\nConnexion au site BCEAO...")

    homepage = get_homepage(session)

    reports = extract_reports(homepage)

    print(f"\nNombre de rapports détectés : {len(reports)}")

    if not reports:
        print("Aucun rapport détecté. Vérifie la page d'accueil.")
        return

    successful = []
    failed = []

    for index, report in enumerate(reports, start=1):

        print("\n" + "=" * 65)
        print(f"Rapport {index}/{len(reports)}")
        print(report["title"])
        print("Identifiant :", report["id_tab"])
        print("Fréquence :", report["frequency"])

        try:

            # Ouvrir le formulaire du rapport
            report_page = open_report(session, report)

            form = report_page.find(
                "form",
                id="form_consultation"
            )

            if form is None:
                raise ValueError(
                    "Formulaire de configuration introuvable."
                )

            # Détecter tous les pays
            countries = detect_countries(form)

            print("Pays détectés :", countries)

            # Construire les paramètres
            params = build_params(
                report["frequency"],
                countries
            )

            print("Paramètres :", params)

            # Générer le rapport
            result_page = generate_report(
                session,
                report,
                report_page,
                countries,
                params
            )

            # Télécharger le fichier
            filepath = download_report(
                session,
                report,
                result_page,
                params
            )

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

        # Petite pause entre les requêtes
        time.sleep(2)

    # Enregistrer le bilan
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