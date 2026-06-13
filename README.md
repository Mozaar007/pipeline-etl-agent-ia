[🇫🇷 Français](README.md) · [🇬🇧 English](README.en.md)

# 📊 Pipeline ETL Intelligent — Analyse des Ventes avec Agent IA

> Un pipeline de données complet qui ne se contente pas de déplacer des données : il les lit, les comprend, et vous dit ce qu'il faut en faire.

![Dashboard Global](assets/dashboard_global_view.png)

---

## Pourquoi ce projet existe

La plupart des pipelines ETL s'arrêtent au chargement. Les données arrivent dans l'entrepôt, propres et agrégées — et puis c'est à un humain de les analyser, d'écrire un rapport, d'identifier les anomalies, de formuler des recommandations.

Ce projet pousse le raisonnement un cran plus loin : une fois les données chargées, un **agent IA (Claude via l'API Anthropic)** prend le relais. Il interroge l'entrepôt, détecte les tendances et les anomalies, et produit automatiquement un rapport analytique en langage naturel — structuré, actionnable, sans intervention humaine.

C'est un pipeline ETL classique augmenté d'une couche d'intelligence.

---

## Ce que fait concrètement ce pipeline

**Données en entrée :** ventes e-commerce sur 12 mois, issues de 3 sources hétérogènes
- `web_orders.json` — commandes du site web (format API REST, avec ~2% de doublons)
- `pos_sales.csv` — export caisse des points de vente physiques (libellés bruités, quantités manquantes)
- `social_orders.db` — commandes via réseaux sociaux en SQLite (prix en texte, dates au format DD/MM/YYYY, quantités parfois en lettres : "deux", "trois"...)

**Ce que le pipeline produit :**
- Un dataset propre et unifié (8 100 lignes après déduplication)
- Un entrepôt DuckDB avec 4 vues agrégées (par mois, produit, catégorie, canal)
- Un rapport IA en JSON + Markdown avec top produits, tendances, anomalies, recommandations
- Un dashboard Streamlit interactif consultable par un utilisateur non technique

---

## Architecture

```
generate_data.py          ← génère les 3 sources de données simulées
        │
        ▼
src/extract.py            ← lit les 3 sources → schéma unifié (8 colonnes)
        │
        ▼
src/transform.py          ← nettoyage, normalisation, déduplication, enrichissement catalogue
        │
        ▼
src/load.py               ← chargement dans DuckDB + 4 vues agrégées
        │
        ▼
src/agent_insights.py     ← agent Claude : analyse les agrégats → rapport JSON + Markdown
        │
        ▼
dashboard.py              ← dashboard Streamlit (KPIs, graphiques, rapport IA)

pipeline.py               ← orchestre tout avec Prefect (@flow + @task + retries)
```

---

## Stack technique

| Couche | Technologie |
|---|---|
| Extraction | Python, pandas, sqlite3 |
| Transformation | pandas |
| Chargement | DuckDB |
| Orchestration | Prefect |
| Agent IA | API Anthropic (Claude Sonnet) |
| Dashboard | Streamlit + Plotly |
| Langage | Python 3.11 |

---

## Captures d'écran

### Dashboard — Vue globale (KPIs + tendances mensuelles)
![Vue globale](assets/dashboard_global_view.png)

*Le pic de décembre (+57% vs moyenne mensuelle) et le creux de janvier (-49%) sont immédiatement visibles.*

### Dashboard — Top produits & répartition
![Top produits et donuts](assets/dashboad_top_product_and_donut_chart.png)

### Rapport généré par l'agent IA
![Rapport IA](assets/dashboard_AI_report.png)

### Pipeline Prefect — Exécution complète
![Pipeline Prefect](assets/pipeline_mock_execution_success.png)

### Données sources — Points de vente (CSV)
![POS Data](assets/Point_Of_Sales_Data.png)

### Données sources — Réseaux sociaux (SQLite)
![Social Orders](assets/social_media_orders.png)

---

## Installation et lancement

### Prérequis
- Python 3.11+
- Git

### 1. Cloner le repo
```bash
git clone https://github.com/Mozaar007/pipeline-etl-agent-ia.git
cd pipeline-etl-agent-ia
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer la clé API (optionnel — pour l'agent réel)
Créer un fichier `.env` à la racine :
```
ANTHROPIC_API_KEY=sk-ant-ta-clé-ici
```

### 4. Générer les données sources
```bash
python generate_data.py
```

### 5. Lancer le pipeline complet

**Avec agent mock (sans crédit API) :**
```bash
python pipeline.py --mock
```

**Avec agent réel (Claude API) :**
```bash
python pipeline.py
```

### 6. Lancer le dashboard
```bash
streamlit run dashboard.py
```
Ouvre automatiquement sur `http://localhost:8501`

---

## Structure du repo

```
pipeline-etl-agent-ia/
├── src/
│   ├── extract.py              ← lecture et unification des 3 sources
│   ├── transform.py            ← nettoyage et enrichissement
│   ├── load.py                 ← chargement DuckDB + vues agrégées
│   ├── agent_insights.py       ← agent IA (Claude API)
│   └── agent_insights_mock.py  ← version mock (sans crédit API)
├── data/
│   ├── products.csv            ← catalogue produits (référentiel maître)
│   ├── raw/                    ← données sources brutes
│   └── processed/              ← datasets intermédiaires (gitignorés)
├── reports/                    ← rapports IA générés (JSON + Markdown)
├── assets/                     ← captures d'écran et visuels
├── notebooks/                  ← scripts d'exploration
├── pipeline.py                 ← orchestration Prefect
├── dashboard.py                ← dashboard Streamlit
├── generate_data.py            ← générateur de données simulées
├── requirements.txt
└── .env.example
```

---

## Choix techniques assumés

**DuckDB plutôt que PostgreSQL** : pas de serveur à installer, fichier unique portable, syntaxe SQL identique à Postgres. Un recruteur qui clone le repo peut lancer le pipeline en 2 minutes sans configuration.

**Données simulées mais réalistes** : les 3 sources ont des schémas volontairement hétérogènes (formats de date différents, prix en texte, quantités en lettres, libellés bruités) pour rendre le travail de transformation démontrable et non trivial.

**Imputation des quantités manquantes à 1** : les ~15 lignes POS avec quantité vide sont imputées à 1 (hypothèse : vente unitaire la plus fréquente). C'est une décision de modélisation documentée, pas un oubli.

**Chargement full refresh** : `load.py` recrée la table à chaque exécution. Dans un pipeline incrémental en production, on adopterait une stratégie upsert. C'est une limite assumée pour cette démo.

---

## Résultats clés (12 mois)

- **Revenue total :** 165 594 000 XAF
- **Marge totale :** 80 907 500 XAF (taux : 48,9%)
- **Commandes traitées :** 8 100 (après déduplication de 73 doublons)
- **Pic saisonnier :** Décembre 2025 (+57% vs moyenne)
- **Creux :** Janvier 2026 (-49% vs moyenne)
- **Canal dominant :** Website (43,7% du revenue)
- **Catégorie la plus rentable :** Mode (54% de taux de marge vs 43% pour l'Électronique)

---

## Contact

**Bobby Mozaar — BigIcks Consulting**
Agence spécialisée en agents IA et automatisation intelligente pour institutions francophones africaines.

- 📧 smozaar@gmail.com
- 📱 +237 673 687 079
- 🐙 [github.com/Mozaar007](https://github.com/Mozaar007)

---

*Données générées à des fins de démonstration. Ce projet fait partie d'un roadmap de 38 projets en Data Engineering et IA.*
