
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import pandas as pd

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

    form = soup.find("form", id="form_consultation")

    if not form:
        print("Consultation form not found!")
        print("Page title:", soup.title.get_text(strip=True)
              if soup.title else "No title")
        return None

    print("\nConsultation form found!")

    # Inspect country checkboxes
    countries = form.find_all(
        "input",
        attrs={"type": "checkbox"}
    )

    print("Country checkboxes:",
          [field.get("name") for field in countries])

    # Inspect available years
    for name in ["annee_debut", "annee_fin"]:
        select = form.find("select", attrs={"name": name})

        if select:
            options = [
                (option.get("value"), option.get_text(strip=True))
                for option in select.find_all("option")
            ]

            print(f"\n{name}:")
            print("First options:", options[:3])
            print("Last options:", options[-3:])

    print("\nForm action:", form.get("action"))
    print("Form method:", form.get("method"))

    return soup


def generate_report(soup, report, page_url):
    form = soup.find("form", id="form_consultation")

    if not form:
        print("Consultation form not found.")
        return None

    # Identify the form destination
    action_url = urljoin(page_url, form.get("action"))

    # Select all countries
    countries = ["B", "C", "A", "S", "D", "H", "K", "T", "Z"]

    # Period: annual report
    start_year = "1960"
    end_year = "2026"

    frequency = report["frequency"]

    # Construct the parameters string
    params = (
        f"{frequency}*{';'.join(countries)}*"
        f"{start_year}*{end_year}*1*l"
    )

    payload = {
        "idTab": report["id_tab"],
        "frequence": frequency,
        "annee_debut": start_year,
        "annee_fin": end_year,
        "metadonnee": "1",
        "params": params
    }

    # Add country checkboxes
    for country in countries:
        payload[country] = country

    response = session.post(
        action_url,
        data=payload,
        headers={"Referer": page_url},
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    print("\nReport request submitted.")
    print("Status:", response.status_code)
    print("Final URL:", response.url)
    print("History:", [r.status_code for r in response.history])
    print("Content type:", response.headers.get("Content-Type"))

    result_soup = BeautifulSoup(response.text, "html.parser")

    print("Page title:",
          result_soup.title.get_text(strip=True)
          if result_soup.title else "No title")

    print("Tables found:", len(result_soup.find_all("table")))

    print(
        "Response preview:",
        result_soup.get_text(" ", strip=True)[:500]
    )

    return response


def inspect_tables(response):
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")

    print(f"\nTotal tables: {len(tables)}")

    for i, table in enumerate(tables):
        rows = table.find_all("tr")

        print(f"\nTABLE {i}")
        print("Rows:", len(rows))

        if rows:
            for row in rows[:4]:
                cells = row.find_all(["th", "td"])

                print([
                    cell.get_text(" ", strip=True)
                    for cell in cells
                ])



def extract_data(response):
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")

    expected_headers = [
        "CODE",
        "LIBELLE",
        "UNITE DE MESURE",
        "MAGNITUDE",
        "SOURCE",
        "TYPE SERIE",
        "METHODE OBSERVATION"
    ]

    for index, table in enumerate(tables):

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)

            headers = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if headers[:7] == expected_headers:

                print(f"Data table found: {index}")

                data = []

                for data_row in table.find_all("tr"):
                    values = [
                        cell.get_text(" ", strip=True)
                        for cell in data_row.find_all(
                            ["th", "td"],
                            recursive=False
                        )
                    ]

                    if len(values) == len(headers):
                        if values != headers:
                            data.append(values)

                df = pd.DataFrame(data, columns=headers)

                print("\nDataFrame shape:", df.shape)
                print(df.head())

                return df

    print("Structured data table not found.")
    return None



def inspect_countries(response):
    soup = BeautifulSoup(response.text, "html.parser")

    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = heading.get_text(" ", strip=True)

        if title:
            print(title)

if __name__ == "__main__":

    homepage = get_homepage()

    reports = extract_reports(homepage)

    print("\nTotal reports:", len(reports))

    # Test the first report
    first_report = reports[0]

    print("\nTesting:", first_report["title"])

    report_page = open_report(first_report)

    if report_page:
        # Save the selection page URL for the next POST
        response_url = report_page_url = (
            urljoin(BASE_URL, "tableauPredefini.php")
        )

        soup_url = report_page_url

        result = generate_report(
            report_page,
            first_report,
            "https://edenpub.bceao.int/tableauPredefini.php"
        )
        if result:
            #inspect_tables(result)
            #inspect_countries(result)
            df = extract_data(result)

            if df is not None:
                df.to_csv(
                    "bceao_ihpc.csv",
                    index=False,
                    sep=";",
                    encoding="utf-8-sig"
                )

                print("\nCSV exported successfully!")
                
                # Examiner les préfixes des codes
                df["PREFIX"] = df["CODE"].str[:2]

                print(df["PREFIX"].value_counts())
                print("Nombre de préfixes :", df["PREFIX"].nunique())
                print("\nExemples de codes :")
                print(df.groupby("PREFIX")["CODE"].head(3))
            # print("\nShape:", df.shape)
            # print("\nColumns:")
            # print(df.columns.tolist())

            # print("\nMissing values:")
            # print((df == "-").sum().sort_values(ascending=False).head(10))

            # print("\nFirst 10 rows:")
            # print(df.head(10).to_string())
