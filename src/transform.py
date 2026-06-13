"""
transform.py — Étape TRANSFORMATION du pipeline.

Prend le dataset brut unifié (sortie de extract.py) et produit un dataset
propre et enrichi, prêt pour le chargement dans l'entrepôt.

Traitements appliqués :
1. quantity   : conversion en int (gère "deux", "trois"... et valeurs manquantes -> imputées à 1)
2. unit_price : extraction du nombre depuis des formats hétérogènes ("4 500 FCFA", "23800XAF"...)
3. order_datetime : normalisation des 3 formats sources vers un datetime unique
4. Déduplication : suppression des doublons exacts (order_id + product_id + datetime)
5. Enrichissement : jointure avec products.csv (nom officiel, catégorie, coût)
6. Calcul de métriques métier : revenue, cost, margin
"""

import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ----------------------------------------------------------------------
# Mapping des quantités écrites en lettres (source social)
# ----------------------------------------------------------------------
QTY_WORDS = {"un": 1, "deux": 2, "trois": 3, "quatre": 4}


def clean_quantity(value: str) -> int:
    """Convertit une quantité brute (numérique ou en lettres, ou vide) en int."""
    if value is None:
        return 1
    val = str(value).strip().lower()
    if val == "" or val == "nan":
        return 1  # imputation : valeur manquante -> 1 (hypothèse la plus fréquente)
    if val in QTY_WORDS:
        return QTY_WORDS[val]
    try:
        return int(float(val))
    except ValueError:
        return 1  # filet de sécurité pour toute valeur inattendue


def clean_price(value: str) -> float:
    """Extrait un nombre depuis un prix brut hétérogène (ex: '4 500 FCFA', '23800XAF', '15500')."""
    val = str(value)
    # Supprime tout ce qui n'est pas un chiffre ou un point/virgule décimal
    cleaned = re.sub(r"[^\d.,]", "", val)
    cleaned = cleaned.replace(",", ".")
    if cleaned == "":
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_datetime(value: str) -> pd.Timestamp:
    """
    Normalise les 3 formats de date sources :
      - Web    : '2025-06-10T14:32:00Z'   (ISO 8601)
      - POS    : '2025-06-10 14:32'       (date + heure séparées, recombinées dans extract.py)
      - Social : '10/06/2025 14:32'       (DD/MM/YYYY)
    """
    val = str(value).strip()

    # Format web (ISO avec 'T' et 'Z')
    if "T" in val:
        return pd.to_datetime(val, format="%Y-%m-%dT%H:%M:%SZ", errors="coerce")

    # Format social (DD/MM/YYYY HH:MM)
    if "/" in val:
        return pd.to_datetime(val, format="%d/%m/%Y %H:%M", errors="coerce")

    # Format POS (YYYY-MM-DD HH:MM)
    return pd.to_datetime(val, format="%Y-%m-%d %H:%M", errors="coerce")


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les doublons exacts (mêmes order_id, product_id, datetime, quantité, prix)."""
    before = len(df)
    df = df.drop_duplicates(
        subset=["order_id", "product_id", "order_datetime", "quantity", "unit_price"],
        keep="first"
    )
    removed = before - len(df)
    print(f"Déduplication : {removed} ligne(s) supprimée(s)")
    return df


def enrich_with_catalog(df: pd.DataFrame) -> pd.DataFrame:
    """Joint avec products.csv pour récupérer le nom officiel, la catégorie et le coût."""
    catalog = pd.read_csv(DATA_DIR / "products.csv", dtype={"product_id": str})

    merged = df.merge(
        catalog[["product_id", "nom", "categorie", "cout"]],
        on="product_id",
        how="left"
    )

    # Le nom officiel du catalogue remplace le libellé brut (potentiellement bruité)
    merged["product_name"] = merged["nom"]
    merged["category"] = merged["categorie"]
    merged["unit_cost"] = merged["cout"]

    merged = merged.drop(columns=["nom", "categorie", "cout", "product_label"])
    return merged


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Applique toute la chaîne de transformation au DataFrame brut unifié."""
    df = df.copy()

    print("Nettoyage des quantités...")
    df["quantity"] = df["quantity"].apply(clean_quantity)

    print("Nettoyage des prix...")
    df["unit_price"] = df["unit_price"].apply(clean_price)

    print("Normalisation des dates...")
    df["order_datetime"] = df["order_datetime"].apply(clean_datetime)
    # Lignes dont la date n'a pas pu être parsée -> rejetées
    before = len(df)
    df = df.dropna(subset=["order_datetime"])
    if before - len(df) > 0:
        print(f"  {before - len(df)} ligne(s) avec date invalide supprimée(s)")

    print("Déduplication...")
    df = deduplicate(df)

    print("Enrichissement via le catalogue produits...")
    df = enrich_with_catalog(df)

    print("Calcul des métriques métier (revenue, cost, margin)...")
    df["revenue"] = df["quantity"] * df["unit_price"]
    df["cost"] = df["quantity"] * df["unit_cost"]
    df["margin"] = df["revenue"] - df["cost"]

    # Colonnes additionnelles pour l'analyse temporelle
    df["order_date"] = df["order_datetime"].dt.date
    df["year_month"] = df["order_datetime"].dt.to_period("M").astype(str)

    # Réordonnancement final des colonnes
    final_columns = [
        "order_id", "product_id", "product_name", "category",
        "quantity", "unit_price", "unit_cost",
        "revenue", "cost", "margin",
        "order_datetime", "order_date", "year_month",
        "channel", "source_detail"
    ]
    return df[final_columns]


if __name__ == "__main__":
    raw_path = DATA_DIR / "processed" / "extracted_raw.csv"
    raw_df = pd.read_csv(raw_path, dtype=str)

    clean_df = transform(raw_df)

    print(f"\nTotal lignes après transformation : {len(clean_df)}")
    print("\nAperçu :")
    print(clean_df.head(10))

    print("\nStatistiques rapides :")
    print(f"  Revenue total      : {clean_df['revenue'].sum():,.0f} XAF")
    print(f"  Margin total       : {clean_df['margin'].sum():,.0f} XAF")
    print(f"  Période couverte   : {clean_df['order_date'].min()} -> {clean_df['order_date'].max()}")

    out_path = DATA_DIR / "processed" / "sales_clean.csv"
    clean_df.to_csv(out_path, index=False)
    print(f"\nFichier écrit : {out_path}")