"""
Auditoría del export: cobertura temporal, volúmenes por industria,
calidad de filing_date, distribución de estados y muestra de applicants.

Uso: .venv/bin/python scripts/audit.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_parquet(ROOT / "data" / "marcas.parquet")

pd.set_option("display.width", 200)
print(f"Total filas: {len(df)}\n")

print("== Filas por year (campo del dataset) ==")
print(df["year"].value_counts().sort_index().to_string(), "\n")

print("== Calidad filing_date ==")
fd = pd.to_datetime(df["filing_date"], errors="coerce")
print(f"nulos: {df['filing_date'].isna().sum()}  no-parseables: {(fd.isna() & df['filing_date'].notna()).sum()}")
print("por año de filing_date:")
print(fd.dt.year.value_counts().sort_index().to_string(), "\n")

print("== sign_type ==")
print(df["sign_type"].value_counts(dropna=False).to_string(), "\n")

print("== type_name ==")
print(df["type_name"].value_counts(dropna=False).head(15).to_string(), "\n")

print("== status ==")
print(df["status"].value_counts(dropna=False).head(20).to_string(), "\n")

print("== Volúmenes por industria (clases de Niza) ==")
INDUSTRIAS = {
    "Software/Tech (9,42)": {9, 42},
    "Comida (29,30)": {29, 30},
    "Bebidas (32)": {32},
    "Alcohol (33)": {33},
    "Minería (6,37,40)": {6, 37, 40},
    "Energía (4,39,40)": {4, 39, 40},
}
classes = df["niza_classes"]
for nombre, cls in INDUSTRIAS.items():
    mask = classes.apply(lambda l: bool(cls & set(l)) if l is not None and len(l) else False)
    print(f"{nombre}: {mask.sum()}")
print()

print("== niza_classes vacías ==")
print(classes.apply(lambda l: l is None or len(l) == 0).sum(), "\n")

print("== applicant_country ==")
print(f"cobertura: {df['applicant_country'].notna().mean():.1%}")
print(df["applicant_country"].value_counts().head(12).to_string(), "\n")
cl = (df["applicant_country"] == "CL")
print(f"CL: {cl.sum()}  extranjeros: {(df['applicant_country'].notna() & ~cl).sum()}\n")

print("== Muestra de brand_name ==")
print(df["brand_name"].dropna().sample(20, random_state=2).to_string())
