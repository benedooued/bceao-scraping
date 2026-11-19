import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pandas as pd

import config
from client import create_session, request_with_retry
from scrapers import extract_reports, detect_countries, build_params, serialize_form, set_payload_value
from storage import save_report_file

def process_single_report(session, report):
    # Step 1: Fetch form configuration page
    url_config = urljoin(config.BASE_URL, "tableauPredefini.php")
    resp_config = request_with_retry(
        session, "POST", url_config, 
        data={"frequence": report["frequency"], "idTab": report["id_tab"], "libelleTab": report["title"]},
        headers={"Referer": config.HOME_URL}
    )
    report_page = BeautifulSoup(resp_config.text, "html.parser")
    form = report_page.find("form", id="form_consultation")
    if not form:
        raise ValueError("form_consultation missing.")

    # Step 2: Prepare parameters and payload
    countries = detect_countries(form)
    params = build_params(report["frequency"], countries)
    
    action = form.get("action") or "rapportPredefini.php"
    gen_url = urljoin(config.BASE_URL, action)
    payload = serialize_form(form, countries)
    payload = set_payload_value(payload, "params", params)
    payload = set_payload_value(payload, "idTab", report["id_tab"])

    # Step 3: Generate result page
    resp_result = request_with_retry(session, "POST", gen_url, data=payload, headers={"Referer": gen_url})
    result_page = BeautifulSoup(resp_result.text, "html.parser")

    # Step 4: Download exported file
    export_form = next((f for f in result_page.find_all("form") if "export" in f.get("action", "").lower()), None)
    if export_form:
        export_url = urljoin(config.BASE_URL, export_form.get("action"))
        export_payload = serialize_form(export_form)
    else:
        export_url = urljoin(config.BASE_URL, "exportTableauPredefiniEnColonne.php")
        export_payload = []

    export_payload = set_payload_value(export_payload, "params", params)
    export_payload = set_payload_value(export_payload, "idTab", report["id_tab"])
    export_payload = set_payload_value(export_payload, "export", "")

    file_resp = request_with_retry(session, "POST", export_url, data=export_payload, headers={"Referer": config.HOME_URL})
    
    if "html" in file_resp.headers.get("Content-Type", "").lower():
        raise ValueError("Server returned HTML page instead of expected data file.")

    return save_report_file(file_resp.content, report["id_tab"], report["title"])

def main():
    session = create_session()
    print("Connecting to BCEAO portal...")
    
    home_resp = request_with_retry(session, "GET", config.HOME_URL)
    homepage = BeautifulSoup(home_resp.text, "html.parser")
    reports = extract_reports(homepage)

    successful, failed = [], []

    for index, report in enumerate(reports, start=1):
        print(f"\nProcessing [{index}/{len(reports)}]: {report['title']}")
        try:
            filepath = process_single_report(session, report)
            print(f"  Success -> Saved to {filepath}")
            successful.append({**report, "file": str(filepath)})
        except Exception as error:
            print(f"  Failed -> {error}")
            failed.append({**report, "error": str(error)})
        
        time.sleep(2)

    pd.DataFrame(successful).to_csv(config.OUTPUT_DIR / "successful_exports.csv", index=False)
    pd.DataFrame(failed).to_csv(config.OUTPUT_DIR / "failed_exports.csv", index=False)

if __name__ == "__main__":
    main()