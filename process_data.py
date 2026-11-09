
import re
import csv
from pathlib import Path

import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

INPUT_DIR = Path("exports")
OUTPUT_DIR = Path("processed")

OUTPUT_DIR.mkdir(exist_ok=True)

# Formats de dates reconnus
MONTHS = {
    "JAN": 1, "JANV": 1,
    "FEB": 2, "FEV": 2, "FÉV": 2,
    "MAR": 3, "MARS": 3,
    "APR": 4, "AVR": 4,
    "MAY": 5, "MAI": 5,
    "JUN": 6, "JUIN": 6,
    "JUL": 7, "JUIL": 7,
    "AUG": 8, "AOU": 8, "AOÛ": 8,
    "SEP": 9, "SEPT": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12, "DÉC": 12
}


# =========================================================
# 1. IDENTIFIER LES COLONNES TEMPORELLES
# =========================================================

def detect_date_columns(df):

    date_columns = {}

    for col in df.columns:

        name = str(col).strip().upper()
        name = name.replace("_", "").replace("-", "").replace(" ", "")

        # Format : JAN2020, FEV2021, etc.
        match = re.match(
            r"^([A-ZÉÛ]+)(\d{4})$",
            name
        )

        if match:

            month_name, year = match.groups()

            month = MONTHS.get(month_name)

            if month:
                date_columns[col] = pd.Timestamp(
                    int(year), month, 1
                )

                continue

        # Format : 2020-01
        match = re.match(
            r"^(\d{4})-(\d{1,2})$",
            str(col).strip()
        )

        if match:

            year, month = map(int, match.groups())

            if 1 <= month <= 12:
                date_columns[col] = pd.Timestamp(
                    year, month, 1
                )

                continue

        # Format annuel : 2020
        match = re.match(
            r"^(?:ANNEE|YEAR)?(\d{4})$",
            name
        )

        if match:
            year = int(match.group(1))

            if 1900 <= year <= 2100:
                date_columns[col] = pd.Timestamp(year, 1, 1)

    return date_columns


# =========================================================
# 2. LIRE LES EXPORTS BCEAO TEXTE
# =========================================================

def read_bceao_text(filepath):

    encodings = ["utf-8-sig", "cp1252", "latin-1"]

    lines = None

    for encoding in encodings:
        try:
            lines = filepath.read_text(
                encoding=encoding
            ).splitlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None:
        raise ValueError("Impossible de lire le fichier.")

    records = []

    country = None
    headers = None

    for line in lines:

        line = line.strip().lstrip("\ufeff")

        if not line:
            continue

        # Détection de l'en-tête du tableau
        if line.upper().startswith("CODE;"):

            headers = [
                x.strip()
                for x in line.split(";")
            ]

            # Supprimer les colonnes vides finales
            while headers and not headers[-1]:
                headers.pop()

            continue

        # Détection du pays
        if headers is None and line.endswith(";"):

            parts = line.split(";")

            if len(parts) <= 2 and parts[0].strip():

                country = parts[0].strip()
                continue

        if headers is None:
            continue

        # Lecture de la ligne de données
        values = next(
            csv.reader(
                [line],
                delimiter=";",
                quotechar='"'
            )
        )

        # Supprimer les séparateurs finaux
        while values and values[-1] == "":
            values.pop()

        # Compléter les éventuelles valeurs manquantes
        values = values[:len(headers)]
        values += [None] * (len(headers) - len(values))

        record = dict(zip(headers, values))

        record["PAYS"] = country

        records.append(record)

    if not records:
        raise ValueError(
            "Aucune ligne de données trouvée dans le fichier."
        )

    return pd.DataFrame(records)


# =========================================================
# 3. LIRE CSV OU EXCEL
# =========================================================

def read_export(filepath):

    with open(filepath, "rb") as file:
        signature = file.read(8)

    # Fichier Excel XLSX
    if signature.startswith(b"PK"):
        return pd.read_excel(filepath)

    # Ancien fichier Excel XLS
    if signature.startswith(bytes.fromhex("D0CF11E0")):
        return pd.read_excel(filepath)

    # Export texte / CSV BCEAO
    return read_bceao_text(filepath)


# =========================================================
# 4. NETTOYAGE GENERAL
# =========================================================

def clean_dataframe(df):

    df = df.copy()

    # Nettoyer les noms de colonnes
    df.columns = [
        str(col).strip().upper()
        for col in df.columns
    ]

    # Supprimer les colonnes complètement vides
    df = df.dropna(axis=1, how="all")

    # Nettoyer les espaces dans les valeurs textuelles
    for col in df.select_dtypes(include="object").columns:

        df[col] = df[col].apply(
            lambda x: x.strip() if isinstance(x, str) else x
        )

        df[col] = df[col].replace("", pd.NA)

    # Supprimer les lignes entièrement vides
    df = df.dropna(how="all")

    return df


# =========================================================
# 5. CONVERSION DES VALEURS NUMERIQUES
# =========================================================

def convert_numeric_columns(df, date_columns):

    df = df.copy()

    for col in date_columns:

        if col not in df.columns:
            continue

        values = (
            df[col]
            .astype("string")
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        df[col] = pd.to_numeric(
            values,
            errors="coerce"
        )

    return df


# =========================================================
# 6. AJOUTER LES INFORMATIONS SUR LE RAPPORT
# =========================================================

def add_report_metadata(df, filepath):

    df = df.copy()

    filename = filepath.stem

    match = re.match(r"^(\d+)_?(.*)$", filename)

    if match:
        report_id = match.group(1)
        report_name = match.group(2)
    else:
        report_id = None
        report_name = filename

    df["REPORT_ID"] = report_id
    df["REPORT_NAME"] = report_name
    df["SOURCE_FILE"] = filepath.name

    return df


# =========================================================
# 7. TRANSFORMATION WIDE VERS LONG
# =========================================================

def to_long_format(df):

    date_columns = detect_date_columns(df)

    if not date_columns:
        return pd.DataFrame()

    date_cols = list(date_columns.keys())

    id_columns = [
        col for col in df.columns
        if col not in date_cols
    ]

    long_df = df.melt(
        id_vars=id_columns,
        value_vars=date_cols,
        var_name="PERIODE_SOURCE",
        value_name="VALEUR"
    )

    # Ajouter une vraie date
    long_df["DATE"] = long_df[
        "PERIODE_SOURCE"
    ].map(date_columns)

    long_df["ANNEE"] = long_df["DATE"].dt.year

    long_df["MOIS"] = long_df["DATE"].dt.month

    long_df["FREQUENCE"] = long_df["MOIS"].apply(
        lambda x: "MENSUELLE" if pd.notna(x) else "ANNUELLE"
    )

    long_df["VALEUR"] = pd.to_numeric(
        long_df["VALEUR"]
        .astype("string")
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )

    return long_df


# =========================================================
# 8. TRAITEMENT DE TOUS LES FICHIERS
# =========================================================

def process_all_exports():

    files = [
        f for f in INPUT_DIR.iterdir()
        if f.is_file()
        and f.suffix.lower() in [".csv", ".xls", ".xlsx"]
        and not f.name.startswith("successful_exports")
        and not f.name.startswith("failed_exports")
    ]

    print(f"{len(files)} fichiers trouvés.")

    wide_dfs = []
    long_dfs = []

    quality_reports = []
    errors = []

    for index, filepath in enumerate(files, start=1):

        print(
            f"\n[{index}/{len(files)}] Traitement : {filepath.name}"
        )

        try:

            # Lire
            df = read_export(filepath)

            # Nettoyer
            df = clean_dataframe(df)

            # Identifier les colonnes temporelles
            date_columns = detect_date_columns(df)

            # Convertir les valeurs
            df = convert_numeric_columns(
                df,
                date_columns
            )

            # Ajouter les métadonnées
            df = add_report_metadata(
                df,
                filepath
            )

            # Supprimer les doublons
            duplicates = df.duplicated().sum()

            df = df.drop_duplicates()

            # Transformation long
            long_df = to_long_format(df)

            # Stockage
            wide_dfs.append(df)

            if not long_df.empty:
                long_dfs.append(long_df)

            # Qualité des données
            quality_reports.append({

                "FILE": filepath.name,

                "ROWS": len(df),

                "COLUMNS": len(df.columns),

                "DUPLICATES_REMOVED": duplicates,

                "MISSING_VALUES": int(
                    df.isna().sum().sum()
                ),

                "MISSING_PERCENT": round(
                    df.isna().sum().sum()
                    / max(df.size, 1) * 100,
                    2
                ),

                "DATE_COLUMNS": len(date_columns),

                "COUNTRIES": (
                    df["PAYS"].nunique()
                    if "PAYS" in df.columns else 0
                )

            })

            print("  Succès :", df.shape)

        except Exception as error:

            print("  Erreur :", error)

            errors.append({
                "FILE": filepath.name,
                "ERROR": str(error)
            })

    # =====================================================
    # 9. FUSION DES DONNEES
    # =====================================================

    if wide_dfs:

        wide_final = pd.concat(
            wide_dfs,
            ignore_index=True,
            sort=False
        )

        wide_final.to_csv(
            OUTPUT_DIR / "bceao_wide.csv",
            index=False,
            encoding="utf-8-sig"
        )

        print("\nFichier wide créé.")

    else:
        wide_final = pd.DataFrame()

    if long_dfs:

        long_final = pd.concat(
            long_dfs,
            ignore_index=True,
            sort=False
        )

        long_final.to_csv(
            OUTPUT_DIR / "bceao_long.csv",
            index=False,
            encoding="utf-8-sig"
        )

        # Parquet : pratique pour Python et les gros volumes
        try:
            long_final.to_parquet(
                OUTPUT_DIR / "bceao_long.parquet",
                index=False
            )
        except ImportError:
            print(
                "Parquet non créé : installe pyarrow."
            )

        print("\nFichier long créé.")

    else:
        long_final = pd.DataFrame()

    # =====================================================
    # 10. RAPPORT DE QUALITE
    # =====================================================

    pd.DataFrame(quality_reports).to_csv(
        OUTPUT_DIR / "data_quality.csv",
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(errors).to_csv(
        OUTPUT_DIR / "processing_errors.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # =====================================================
    # 11. RESUME
    # =====================================================

    print("\n" + "=" * 55)
    print("TRAITEMENT TERMINE")
    print("=" * 55)

    print("Fichiers traités :", len(wide_dfs))
    print("Erreurs :", len(errors))

    print("Wide :", wide_final.shape)
    print("Long :", long_final.shape)

    print("\nRésultats :", OUTPUT_DIR.resolve())


if __name__ == "__main__":
    process_all_exports()
