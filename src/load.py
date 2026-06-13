"""
load.py — Étape CHARGEMENT du pipeline.

Charge le dataset propre (sales_clean.csv) dans un entrepôt de données DuckDB
(fichier local, pas de serveur requis), et crée des vues agrégées prêtes
pour l'analyse / le dashboard / l'agent IA.

Tables/vues créées :
    fact_sales              : table de faits (une ligne par commande)
    v_sales_by_month        : revenue/margin/quantité par mois
    v_sales_by_product      : revenue/margin/quantité par produit
    v_sales_by_category     : revenue/margin par catégorie
    v_sales_by_channel       : revenue/margin par canal de vente
"""

from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "warehouse.duckdb"


def load(df: pd.DataFrame) -> None:
    """Crée/remplace l'entrepôt DuckDB avec la table de faits et les vues agrégées."""
    conn = duckdb.connect(str(DB_PATH))

    print("Création de la table fact_sales...")
    conn.execute("DROP TABLE IF EXISTS fact_sales")
    conn.execute("CREATE TABLE fact_sales AS SELECT * FROM df")

    print("Création des vues agrégées...")

    conn.execute("""
        CREATE OR REPLACE VIEW v_sales_by_month AS
        SELECT
            year_month,
            COUNT(*) AS nb_orders,
            SUM(quantity) AS total_quantity,
            SUM(revenue) AS total_revenue,
            SUM(margin) AS total_margin
        FROM fact_sales
        GROUP BY year_month
        ORDER BY year_month
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW v_sales_by_product AS
        SELECT
            product_id,
            product_name,
            category,
            COUNT(*) AS nb_orders,
            SUM(quantity) AS total_quantity,
            SUM(revenue) AS total_revenue,
            SUM(margin) AS total_margin
        FROM fact_sales
        GROUP BY product_id, product_name, category
        ORDER BY total_revenue DESC
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW v_sales_by_category AS
        SELECT
            category,
            COUNT(*) AS nb_orders,
            SUM(quantity) AS total_quantity,
            SUM(revenue) AS total_revenue,
            SUM(margin) AS total_margin
        FROM fact_sales
        GROUP BY category
        ORDER BY total_revenue DESC
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW v_sales_by_channel AS
        SELECT
            channel,
            COUNT(*) AS nb_orders,
            SUM(quantity) AS total_quantity,
            SUM(revenue) AS total_revenue,
            SUM(margin) AS total_margin
        FROM fact_sales
        GROUP BY channel
        ORDER BY total_revenue DESC
    """)

    # Vérifications rapides
    nb_rows = conn.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
    print(f"\nfact_sales : {nb_rows} lignes chargées")

    print("\nv_sales_by_month :")
    print(conn.execute("SELECT * FROM v_sales_by_month").df())

    print("\nv_sales_by_category :")
    print(conn.execute("SELECT * FROM v_sales_by_category").df())

    print("\nv_sales_by_channel :")
    print(conn.execute("SELECT * FROM v_sales_by_channel").df())

    print("\nTop 5 produits par revenue :")
    print(conn.execute("SELECT * FROM v_sales_by_product LIMIT 5").df())

    conn.close()
    print(f"\nEntrepôt DuckDB écrit : {DB_PATH}")


if __name__ == "__main__":
    clean_path = DATA_DIR / "processed" / "sales_clean.csv"
    df = pd.read_csv(clean_path)
    # order_datetime doit être un vrai datetime pour DuckDB
    df["order_datetime"] = pd.to_datetime(df["order_datetime"])

    load(df)