"""
Consolida los xlsx de data/raw/ (descargados con curl desde datos.gob.cl)
en data/marcas.parquet, con nacionalidad extraída del prefijo (CC) de Applicants.

Uso: .venv/bin/python scripts/consolidate.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "marcas.parquet"

PAIS_RE = re.compile(r"^\((\w{2})\)")


def parse_classes(v):
    if pd.isna(v):
        return []
    out = []
    for tok in str(v).replace(";", ",").split(","):
        tok = tok.strip()
        if tok.isdigit():
            out.append(int(tok))
    return sorted(set(out))


def pais_solicitante(v):
    if pd.isna(v):
        return None
    m = PAIS_RE.match(str(v).strip())
    return m.group(1) if m else None


def fecha(col):
    return pd.to_datetime(col, errors="coerce").dt.strftime("%Y-%m-%d")


def main():
    frames = []
    for f in sorted(RAW.glob("applications-*.xlsx")):
        year = int(f.stem.split("-")[1])
        df = pd.read_excel(f)
        df["year"] = year
        frames.append(df)
        print(f"[{year}] {len(df)} filas")
    full = pd.concat(frames, ignore_index=True)

    out = pd.DataFrame({
        "year": full["year"],
        "application_number": pd.to_numeric(full["ApplicationNumber"], errors="coerce"),
        "brand_name": full["BrandName"].astype("string"),
        "translation": full["Translation"].astype("string"),
        "niza_classes": full["NizaClasses"].apply(parse_classes),
        "status": full["Status"].astype("string"),
        "sign_type": full["SignType"].astype("string"),
        "type_name": full["TypeName"].astype("string"),
        "subtype_name": full["SubtypeName"].astype("string"),
        "applicants": full["Applicants"].astype("string"),
        "applicant_country": full["Applicants"].apply(pais_solicitante).astype("string"),
        "applicant_state": full["StateApplicants"].astype("string"),
        "registration_number": pd.to_numeric(full["RegistrationNumber"], errors="coerce"),
        "filing_date": fecha(full["FilingDate"]),
        "registration_date": fecha(full["RegistrationDate"]),
        "label_description": full["LabelDescription"].astype("string"),
        "protection_description": full["ProtectionDescription"].astype("string"),
    })
    OUT.parent.mkdir(exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"\nListo: {len(out)} filas -> {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")
    print("\nCobertura applicant_country:", out["applicant_country"].notna().mean().round(3))
    print(out["applicant_country"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
