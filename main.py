
from scraper import (
    create_session,
    get_homepage,
    extract_reports,
    open_report,
    download_report_excel
)

# 1. Connexion
session = create_session()

# 2. Récupérer la liste des rapports
homepage = get_homepage(session)
reports = extract_reports(homepage)

# 3. Sélectionner le rapport IPC mensuel
report = next(
    r for r in reports
    if r["id_tab"] == "20"
)

print("Rapport sélectionné :", report["title"])

# 4. Ouvrir le formulaire du rapport
report_page = open_report(session, report)

# 5. Définir les paramètres
countries = ["A", "B", "C", "S", "D", "H", "K", "T"]

start_month = "01"
start_year = "2020"

end_month = "12"
end_year = "2025"

metadata = "1"

# 6. Construire la chaîne de paramètres
params = (
    f"M*{';'.join(countries)}*"
    f"{start_month};{start_year}*"
    f"{end_month};{end_year}*"
    f"{metadata}*l"
)

print("Paramètres :", params)

# 7. Télécharger le fichier
filepath = download_report_excel(
    session,
    report,
    params
)

print("Téléchargement terminé :", filepath)
