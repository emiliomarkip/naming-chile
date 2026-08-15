"""
Export completo de la colección Qdrant `marcas_inapi` a parquet (sin vectores).

Uso:
  .venv/bin/python scripts/export_qdrant.py

Lee QDRANT_URL / QDRANT_API_KEY desde .env en la raíz del proyecto.
Salida: data/marcas.parquet
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

COLLECTION = "marcas_inapi"
BATCH = 1000
OUT = ROOT / "data" / "marcas.parquet"

FIELDS = [
    "year", "application_number", "brand_name", "brand_name_norm",
    "phonetic_key", "translation", "niza_classes", "status", "sign_type",
    "type_name", "applicants", "registration_number", "filing_date",
    "registration_date", "expiration_date", "label_description",
]


def main():
    url, key = os.environ.get("QDRANT_URL"), os.environ.get("QDRANT_API_KEY")
    if not url or not key:
        sys.exit("Faltan QDRANT_URL / QDRANT_API_KEY en .env")

    client = QdrantClient(url=url, api_key=key, timeout=120, check_compatibility=False)
    info = client.get_collection(COLLECTION)
    total = info.points_count
    print(f"Colección {COLLECTION}: {total} puntos. Exportando...")

    rows, offset, done = [], None, 0
    t0 = time.time()
    while True:
        for attempt in range(5):
            try:
                points, offset = client.scroll(
                    collection_name=COLLECTION, limit=BATCH, offset=offset,
                    with_payload=FIELDS, with_vectors=False)
                break
            except Exception as e:
                wait = 2 ** attempt
                print(f"  error ({e}); reintento en {wait}s")
                time.sleep(wait)
        else:
            sys.exit("Demasiados errores consecutivos, abortando")

        for p in points:
            rows.append(p.payload or {})
        done += len(points)
        if done % 50000 < BATCH:
            rate = done / (time.time() - t0)
            print(f"  {done}/{total} ({rate:.0f} pts/s)")
        if offset is None:
            break

    df = pd.DataFrame(rows)
    # niza_classes viene como lista; parquet la guarda bien como list<int>
    OUT.parent.mkdir(exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"Listo: {len(df)} filas -> {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
