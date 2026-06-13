"""
extract.py — Étape EXTRACTION du pipeline.

Lit les 3 sources brutes hétérogènes (web JSON, POS CSV, social SQLite)
et les normalise vers un schéma commun (mêmes colonnes, mêmes types),
SANS nettoyage métier approfondi (ça, c'est le rôle de transform.py).

Schéma cible :
    order_id        : str   - identifiant unique de commande
    product_id      : str   - référence produit (catalogue)
    quantity        : str   - quantité brute (peut contenir des valeurs textuelles, ex: "deux")
    unit_price      : str   - prix brut (peut contenir devise/espaces, ex: "4 500 FCFA")
    order_datetime  : str   - date/heure brute (formats différents selon la source)
    channel         : str   - "website" / "pos" / "social"
    source_detail   : str   - info brute additionnelle (magasin, plateforme...)
    product_label   : str   - libellé produit brut (peut contenir variantes/fautes)

NOTE: quantity et unit_price restent en str volontairement à ce stade —
leur nettoyage/conversion (gestion de "deux", "4 500 FCFA", etc.) est
délégué à transform.py, pour garder une séparation claire des responsabilités.
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

TARGET_COLUMNS = [
    "order_id", "product_id", "quantity", "unit_price",
    "order_datetime", "channel", "source_detail", "product_label"
]


def extract_web_orders() -> pd.DataFrame:
    """Source 'site web' — JSON façon API REST."""
    path = RAW_DIR / "web_orders.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)

    out = pd.DataFrame({
        "order_id": df["order_id"],
        "product_id": df["product_id"],
        "quantity": df["quantity"].astype(str),
        "unit_price": df["unit_price"].astype(str),
        "order_datetime": df["timestamp"],
        "channel": "website",
        "source_detail": df["currency"],   # info brute additionnelle disponible
        "product_label": df["product_name"],
    })
    return out[TARGET_COLUMNS]


def extract_pos_sales() -> pd.DataFrame:
    """Source 'points de vente physiques' — CSV export caisse (';')."""
    path = RAW_DIR / "pos_sales.csv"
    df = pd.read_csv(path, sep=";", dtype=str)

    # Reconstitution d'un datetime brut combinant date et heure
    order_datetime = df["date_vente"].astype(str) + " " + df["heure"].astype(str)

    out = pd.DataFrame({
        "order_id": [f"POS-{i+1:06d}" for i in range(len(df))],  # pas d'ID natif dans l'export caisse
        "product_id": df["code_produit"],
        "quantity": df["qte"],
        "unit_price": df["prix_unitaire"],
        "order_datetime": order_datetime,
        "channel": "pos",
        "source_detail": df["magasin"],
        "product_label": df["libelle_produit"],
    })
    return out[TARGET_COLUMNS]


def extract_social_orders() -> pd.DataFrame:
    """Source 'réseaux sociaux' — SQLite, schéma bruité."""
    path = RAW_DIR / "social_orders.db"
    conn = sqlite3.connect(path)
    df = pd.read_sql("SELECT * FROM social_orders", conn, dtype=str)
    conn.close()

    out = pd.DataFrame({
        "order_id": df["ref_commande"],
        "product_id": df["produit_id"],
        "quantity": df["quantite"],
        "unit_price": df["prix"],
        "order_datetime": df["date_commande"],
        "channel": "social",
        "source_detail": df["plateforme"],
        "product_label": df["produit_nom"],
    })
    return out[TARGET_COLUMNS]


def extract_all() -> pd.DataFrame:
    """Concatène les 3 sources normalisées en un seul DataFrame brut unifié."""
    web = extract_web_orders()
    pos = extract_pos_sales()
    social = extract_social_orders()

    combined = pd.concat([web, pos, social], ignore_index=True)
    return combined


if __name__ == "__main__":
    df = extract_all()
    print(f"Total lignes extraites : {len(df)}")
    print(df["channel"].value_counts())
    print("\nAperçu :")
    print(df.head(10))

    # Sauvegarde intermédiaire (avant transformation) — utile pour debug/inspection
    out_path = DATA_DIR / "processed" / "extracted_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"\nFichier intermédiaire écrit : {out_path}")