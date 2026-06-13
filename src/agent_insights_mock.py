"""
agent_insights_mock.py — Version MOCK de l'agent IA, pour développement/test
SANS consommer de crédits API.

Remplace l'appel réel à Claude par un rapport JSON statique (mais cohérent
avec le schéma attendu), afin de valider toute la plomberie autour :
lecture DuckDB, écriture JSON/Markdown, structure des fichiers.

USAGE TEMPORAIRE UNIQUEMENT — ce fichier ne doit pas remplacer agent_insights.py
dans le repo final ; il sert juste à débloquer le développement en attendant
le crédit API.
"""

from datetime import datetime
from pathlib import Path

from agent_insights import fetch_aggregates, render_markdown, REPORTS_DIR
import json

# Rapport JSON statique, structuré comme une vraie réponse de l'agent,
# mais avec des valeurs cohérentes avec les agrégats réels calculés précédemment.
MOCK_REPORT = {
    "periode_analysee": "Juin 2025 à Mai 2026 (12 mois)",
    "resume_executif": "Sur l'année écoulée, le chiffre d'affaires total atteint environ 165,6 millions XAF avec une marge globale de 80,9 millions XAF (ratio ~49%). L'activité est fortement concentrée sur l'Électronique et marquée par une forte saisonnalité de fin d'année.",
    "top_produits": [
        {"produit": "Casque Bluetooth XR-200", "revenue": 29602370, "commentaire": "Produit le plus performant, à mettre en avant dans les campagnes promotionnelles."},
        {"produit": "Montre Connectée FitTrack", "revenue": 22910080, "commentaire": "Deuxième meilleure vente, fort potentiel de cross-sell avec les accessoires électroniques."},
        {"produit": "Robe Wax Modèle Akwa", "revenue": 19971000, "commentaire": "Meilleur produit Mode, avec une marge relative élevée."}
    ],
    "tendances_temporelles": {
        "observation_principale": "Une saisonnalité marquée est observée, avec un pic net en décembre et un creux prononcé en janvier et août.",
        "pic": {"periode": "Décembre 2025", "detail": "1324 commandes, soit environ +57% par rapport à la moyenne mensuelle, probablement lié aux achats de fin d'année."},
        "creux": {"periode": "Janvier 2026", "detail": "402 commandes, soit environ -49% par rapport à la moyenne, traduisant un ralentissement post-fêtes classique."}
    },
    "analyse_canaux": {
        "observation": "Le site web génère le revenue le plus élevé (72,4M XAF), suivi des points de vente physiques (51,5M XAF) et des réseaux sociaux (41,7M XAF). Les trois canaux restent significatifs, suggérant une stratégie omnicanale équilibrée.",
        "canal_dominant": "website"
    },
    "analyse_categories": {
        "observation": "L'Électronique domine en volume de revenue (91,7M XAF) mais la Mode affiche un meilleur taux de marge relatif (~54% contre ~43% pour l'Électronique), ce qui en fait une catégorie particulièrement rentable malgré un volume moindre.",
        "categorie_plus_rentable": "Mode"
    },
    "anomalies_detectees": [
        "La baisse d'activité en août (438 commandes, la plus faible après janvier) pourrait indiquer un effet saisonnier (vacances) à anticiper dans la planification des stocks.",
        "L'écart de performance entre l'Électronique (fort volume, marge moyenne) et la Mode (volume moindre, forte marge) suggère un potentiel de rééquilibrage de l'offre."
    ],
    "recommandations": [
        "Anticiper le pic de décembre en augmentant les stocks d'Électronique et de Mode dès novembre, avec des campagnes promotionnelles ciblées.",
        "Lancer des promotions spécifiques en janvier et août pour atténuer les creux saisonniers (ex: ventes flash, offres groupées).",
        "Renforcer la mise en avant de la catégorie Mode, dont la marge relative est supérieure, via le canal website qui est le plus performant.",
        "Étudier le potentiel des réseaux sociaux (41,7M XAF de revenue déjà significatif) pour des campagnes ciblées sur les produits à forte marge."
    ]
}


def run_mock():
    print("[MOCK] Lecture des agrégats depuis l'entrepôt DuckDB...")
    aggregates = fetch_aggregates()  # valide que DuckDB fonctionne
    print(f"[MOCK] {len(aggregates['by_month'])} mois, {len(aggregates['by_product'])} produits chargés.")

    print("[MOCK] Génération du rapport (statique, sans appel API)...")
    report = MOCK_REPORT

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    timestamp = datetime.now().strftime("%Y-%m-%d")

    REPORTS_DIR.mkdir(exist_ok=True)

    json_path = REPORTS_DIR / f"insights_{timestamp}_MOCK.json"
    md_path = REPORTS_DIR / f"insights_{timestamp}_MOCK.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report, generated_at))

    print(f"\n[MOCK] Rapport JSON : {json_path}")
    print(f"[MOCK] Rapport Markdown : {md_path}")
    print("\n--- Résumé exécutif (mock) ---")
    print(report["resume_executif"])


if __name__ == "__main__":
    run_mock()