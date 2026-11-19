from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://edenpub.bceao.int/"
HOME_URL = urljoin(BASE_URL, "rapportPredefini.php")

OUTPUT_DIR = Path("exports_bceao")
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

