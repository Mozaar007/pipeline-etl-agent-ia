"""
agent_insights.py — Couche AGENT IA du pipeline.

À chaque exécution réussie du pipeline ETL, ce module :
1. Interroge les vues agrégées de l'entrepôt DuckDB (résumés, pas le détail ligne par ligne)
2. Envoie ces agrégats à Claude (API Anthropic) avec un prompt structuré
3. Reçoit en retour un rapport JSON structuré (top produits, tendances, anomalies, recommandations)
4. Sauvegarde le rapport en JSON (pour le dashboard) et en Markdown (pour lecture humaine)

Prérequis :
    - variable d'environnement ANTHROPIC_API_KEY définie
    - pip install anthropic duckdb pandas
"""

import json
import os
from datetime import datetime
from pathlib import Path

import anthropic
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "warehouse.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Tu es un analyste data senior spécialisé dans le e-commerce.
Tu reçois des données agrégées de vente (par mois, par produit, par catégorie, par canal)
et tu dois produire une analyse synthétique et actionnable pour un dirigeant non technique.

Règles :
- Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après, sans balises markdown (pas de ```json).
- Toutes les analyses doivent être en français.
- Base-toi strictement sur les chiffres fournis, ne pas inventer de données.
- Sois précis avec les chiffres (montants en XAF, pourcentages calculés correctement).

Structure JSON attendue :
{
  "periode_analysee": "string décrivant la période",
  "resume_executif": "2-3 phrases de synthèse globale",
  "top_produits": [
    {"produit": "nom", "revenue": nombre, "commentaire": "string"}
  ],
  "tendances_temporelles": {
    "observation_principale": "string",
    "pic": {"periode": "string", "detail": "string"},
    "creux": {"periode": "string", "detail": "string"}
  },
  "analyse_canaux": {
    "observation": "string",
    "canal_dominant": "string"
  },
  "analyse_categories": {
    "observation": "string",
    "categorie_plus_rentable": "string"
  },
  "anomalies_detectees": [
    "string décrivant chaque anomalie ou point d'attention"
  ],
  "recommandations": [
    "string : recommandation actionnable et priorisée"
  ]
}
"""


def fetch_aggregates() -> dict:
    """Récupère les agrégats depuis l'entrepôt DuckDB et les formate en dict compact."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    by_month = conn.execute("SELECT * FROM v_sales_by_month").df()
    by_product = conn.execute("SELECT * FROM v_sales_by_product").df()
    by_category = conn.execute("SELECT * FROM v_sales_by_category").df()
    by_channel = conn.execute("SELECT * FROM v_sales_by_channel").df()

    conn.close()

    return {
        "by_month": by_month.to_dict(orient="records"),
        "by_product": by_product.to_dict(orient="records"),
        "by_category": by_category.to_dict(orient="records"),
        "by_channel": by_channel.to_dict(orient="records"),
    }


def build_user_prompt(aggregates: dict) -> str:
    """Construit le prompt utilisateur en injectant les données agrégées en JSON."""
    return f"""Voici les données agrégées de vente sur 12 mois (en XAF) :

VENTES PAR MOIS :
{json.dumps(aggregates['by_month'], ensure_ascii=False, indent=2)}

VENTES PAR PRODUIT (top, déjà trié par revenue décroissant) :
{json.dumps(aggregates['by_product'], ensure_ascii=False, indent=2)}

VENTES PAR CATÉGORIE :
{json.dumps(aggregates['by_category'], ensure_ascii=False, indent=2)}

VENTES PAR CANAL :
{json.dumps(aggregates['by_channel'], ensure_ascii=False, indent=2)}

Produis l'analyse au format JSON décrit dans tes instructions."""


def call_agent(aggregates: dict) -> dict:
    """Appelle l'API Claude pour générer le rapport d'insights."""
    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY depuis l'environnement

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_user_prompt(aggregates)}
        ]
    )

    text = message.content[0].text.strip()

    # Filet de sécurité si le modèle ajoute malgré tout des balises markdown
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    return json.loads(text)


def render_markdown(report: dict, generated_at: str) -> str:
    """Convertit le rapport JSON en document Markdown lisible."""
    lines = []
    lines.append(f"# Rapport d'insights — {report.get('periode_analysee', '')}")
    lines.append(f"\n*Généré automatiquement le {generated_at} par l'agent IA (Claude)*\n")

    lines.append("## Résumé exécutif")
    lines.append(report.get("resume_executif", ""))

    lines.append("\n## Top produits")
    for p in report.get("top_produits", []):
        lines.append(f"- **{p['produit']}** — {p['revenue']:,.0f} XAF : {p['commentaire']}")

    tt = report.get("tendances_temporelles", {})
    lines.append("\n## Tendances temporelles")
    lines.append(tt.get("observation_principale", ""))
    if "pic" in tt:
        lines.append(f"- **Pic** ({tt['pic'].get('periode','')}) : {tt['pic'].get('detail','')}")
    if "creux" in tt:
        lines.append(f"- **Creux** ({tt['creux'].get('periode','')}) : {tt['creux'].get('detail','')}")

    ac = report.get("analyse_canaux", {})
    lines.append("\n## Analyse des canaux de vente")
    lines.append(ac.get("observation", ""))
    lines.append(f"- Canal dominant : **{ac.get('canal_dominant', '')}**")

    acat = report.get("analyse_categories", {})
    lines.append("\n## Analyse des catégories")
    lines.append(acat.get("observation", ""))
    lines.append(f"- Catégorie la plus rentable : **{acat.get('categorie_plus_rentable', '')}**")

    lines.append("\n## Anomalies et points d'attention")
    for a in report.get("anomalies_detectees", []):
        lines.append(f"- {a}")

    lines.append("\n## Recommandations")
    for i, r in enumerate(report.get("recommandations", []), 1):
        lines.append(f"{i}. {r}")

    return "\n".join(lines)


def run():
    print("Lecture des agrégats depuis l'entrepôt DuckDB...")
    aggregates = fetch_aggregates()

    print("Appel de l'agent IA (Claude API)...")
    report = call_agent(aggregates)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    timestamp = datetime.now().strftime("%Y-%m-%d")

    REPORTS_DIR.mkdir(exist_ok=True)

    json_path = REPORTS_DIR / f"insights_{timestamp}.json"
    md_path = REPORTS_DIR / f"insights_{timestamp}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report, generated_at))

    print(f"\nRapport JSON : {json_path}")
    print(f"Rapport Markdown : {md_path}")
    print("\n--- Résumé exécutif ---")
    print(report.get("resume_executif", ""))


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ERREUR : la variable d'environnement ANTHROPIC_API_KEY n'est pas définie.\n"
            "Définis-la avant d'exécuter ce script :\n"
            "  Windows (PowerShell) : $env:ANTHROPIC_API_KEY='ta-clé'\n"
            "  Linux/Mac            : export ANTHROPIC_API_KEY='ta-clé'"
        )
    run()