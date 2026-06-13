"""
pipeline.py — Orchestration du pipeline ETL avec Prefect.

Enchaîne les 4 étapes dans l'ordre :
    1. extract  : lecture des 3 sources brutes → DataFrame unifié
    2. transform : nettoyage, normalisation, enrichissement
    3. load     : chargement dans DuckDB + création des vues agrégées
    4. agent    : génération du rapport d'insights via Claude API (ou mock)

Usage :
    python pipeline.py             → exécution complète (agent réel)
    python pipeline.py --mock      → exécution avec agent mock (sans crédit API)

Prefect UI (optionnel) :
    prefect server start           → lance l'interface locale sur http://127.0.0.1:4200
    python pipeline.py             → l'exécution apparaît dans l'UI
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta

# Ajout du dossier src au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from extract import extract_all
from transform import transform
from load import load

DATA_DIR = Path(__file__).resolve().parent / "data"


# ----------------------------------------------------------------------
# TASKS
# ----------------------------------------------------------------------

@task(
    name="Extraction",
    description="Lit les 3 sources brutes (web JSON, POS CSV, social SQLite) et les unifie.",
    retries=2,
    retry_delay_seconds=10,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
def task_extract() -> pd.DataFrame:
    logger = get_run_logger()
    logger.info("Démarrage de l'extraction...")
    df = extract_all()
    logger.info(f"Extraction terminée : {len(df)} lignes extraites")

    # Sauvegarde intermédiaire pour debug/audit
    out = DATA_DIR / "processed" / "extracted_raw.csv"
    df.to_csv(out, index=False)
    logger.info(f"Fichier intermédiaire écrit : {out}")
    return df


@task(
    name="Transformation",
    description="Nettoyage, normalisation, déduplication et enrichissement catalogue.",
    retries=1,
    retry_delay_seconds=5
)
def task_transform(df: pd.DataFrame) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info(f"Démarrage de la transformation ({len(df)} lignes en entrée)...")
    clean_df = transform(df)
    logger.info(f"Transformation terminée : {len(clean_df)} lignes propres")

    out = DATA_DIR / "processed" / "sales_clean.csv"
    clean_df.to_csv(out, index=False)
    logger.info(f"Dataset propre écrit : {out}")
    return clean_df


@task(
    name="Chargement DuckDB",
    description="Charge le dataset propre dans l'entrepôt DuckDB et crée les vues agrégées.",
    retries=1,
    retry_delay_seconds=5
)
def task_load(df: pd.DataFrame) -> None:
    logger = get_run_logger()
    logger.info("Démarrage du chargement dans DuckDB...")
    df["order_datetime"] = pd.to_datetime(df["order_datetime"])
    load(df)
    logger.info("Chargement terminé : fact_sales + 4 vues agrégées créées")


@task(
    name="Agent IA — Insights",
    description="Génère un rapport d'insights en langage naturel via Claude API.",
    retries=1,
    retry_delay_seconds=30
)
def task_agent(mock: bool = False) -> None:
    logger = get_run_logger()

    if mock:
        logger.info("Mode MOCK activé — aucun appel API Anthropic.")
        from agent_insights_mock import run_mock
        run_mock()
    else:
        logger.info("Appel de l'agent IA (Claude API)...")
        from agent_insights import run
        run()

    logger.info("Rapport d'insights généré dans reports/")


# ----------------------------------------------------------------------
# FLOW PRINCIPAL
# ----------------------------------------------------------------------

@flow(
    name="Pipeline ETL Ventes + Agent IA",
    description="Pipeline complet : extraction → transformation → chargement → insights IA",
)
def etl_pipeline(mock_agent: bool = False):
    logger = get_run_logger()
    logger.info("=== Démarrage du pipeline ETL ===")

    # Étape 1 : Extraction
    raw_df = task_extract()

    # Étape 2 : Transformation (dépend de l'extraction)
    clean_df = task_transform(raw_df)

    # Étape 3 : Chargement (dépend de la transformation)
    task_load(clean_df)

    # Étape 4 : Agent IA (dépend du chargement)
    task_agent(mock=mock_agent)

    logger.info("=== Pipeline terminé avec succès ===")


# ----------------------------------------------------------------------
# POINT D'ENTRÉE
# ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL Ventes + Agent IA")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Utilise l'agent mock (sans crédit API Anthropic)"
    )
    args = parser.parse_args()

    etl_pipeline(mock_agent=args.mock)