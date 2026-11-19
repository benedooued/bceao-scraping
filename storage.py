import re
from pathlib import Path
from config import OUTPUT_DIR



def save_report_file(content: bytes, report_id: str, title: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Check magic bytes to set correct file extension
    if content.startswith(b"PK"):
        extension = ".xlsx"
    elif content.startswith(bytes.fromhex("D0CF11E0")):
        extension = ".xls"
    else:
        extension = ".csv"

    safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title)
    filename = f"{report_id}_{safe_title}{extension}"
    filepath = OUTPUT_DIR / filename
    
    filepath.write_bytes(content)
    return filepath