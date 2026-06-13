"""
Génère les données sources pour le pipeline ETL :
- products.csv (catalogue de référence)
- raw/web_orders.json (source "site web", format API REST)
- raw/pos_sales.csv (source "points de vente physiques", format export caisse)
- raw/social_orders.db (source "réseaux sociaux", SQLite, schéma bruité)

12 mois de données, 12-15 produits, saisonnalité injectée (pic décembre, creux janvier/août).
"""

import csv
import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).parent / "data"
RAW_DIR = OUT_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# 1. CATALOGUE PRODUITS (référentiel commun)
# ----------------------------------------------------------------------
PRODUCTS = [
    {"product_id": "P-0401", "nom": "Casque Bluetooth XR-200", "categorie": "Électronique", "prix_reference": 24500, "cout": 14000},
    {"product_id": "P-0402", "nom": "Chargeur Solaire Portable 20W", "categorie": "Électronique", "prix_reference": 18000, "cout": 9500},
    {"product_id": "P-0403", "nom": "Power Bank 10000mAh", "categorie": "Électronique", "prix_reference": 15000, "cout": 8000},
    {"product_id": "P-0404", "nom": "Montre Connectée FitTrack", "categorie": "Électronique", "prix_reference": 32000, "cout": 19000},
    {"product_id": "P-0405", "nom": "Enceinte Bluetooth Mini", "categorie": "Électronique", "prix_reference": 12000, "cout": 6500},
    {"product_id": "P-0406", "nom": "Robe Wax Modèle Akwa", "categorie": "Mode", "prix_reference": 28000, "cout": 12000},
    {"product_id": "P-0407", "nom": "Chemise Homme Slim Fit", "categorie": "Mode", "prix_reference": 15500, "cout": 7000},
    {"product_id": "P-0408", "nom": "Sac à Main Cuir Bafia", "categorie": "Mode", "prix_reference": 35000, "cout": 18000},
    {"product_id": "P-0409", "nom": "Sandales Cuir Artisanales", "categorie": "Mode", "prix_reference": 12500, "cout": 5500},
    {"product_id": "P-0410", "nom": "Huile de Coco Bio 500ml", "categorie": "Beauté & Soins", "prix_reference": 4500, "cout": 1800},
    {"product_id": "P-0411", "nom": "Savon Noir Artisanal", "categorie": "Beauté & Soins", "prix_reference": 2000, "cout": 700},
    {"product_id": "P-0412", "nom": "Crème Karité Pure 250g", "categorie": "Beauté & Soins", "prix_reference": 3500, "cout": 1300},
    {"product_id": "P-0413", "nom": "Mug Personnalisé Céramique", "categorie": "Maison & Cuisine", "prix_reference": 5000, "cout": 2000},
    {"product_id": "P-0414", "nom": "Set 6 Verres Décorés", "categorie": "Maison & Cuisine", "prix_reference": 9000, "cout": 4000},
]

with open(OUT_DIR / "products.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["product_id", "nom", "categorie", "prix_reference", "cout"])
    writer.writeheader()
    for p in PRODUCTS:
        writer.writerow(p)

print(f"products.csv généré ({len(PRODUCTS)} produits)")

# ----------------------------------------------------------------------
# Helpers : saisonnalité et génération de dates
# ----------------------------------------------------------------------
START_DATE = datetime(2025, 6, 1)
END_DATE = datetime(2026, 5, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

def seasonal_factor(date: datetime) -> float:
    """Pic en décembre (fêtes), creux en janvier et août."""
    month = date.month
    factors = {1: 0.6, 2: 0.8, 3: 0.9, 4: 0.9, 5: 0.95, 6: 1.0,
               7: 0.95, 8: 0.6, 9: 0.9, 10: 1.0, 11: 1.2, 12: 1.8}
    return factors.get(month, 1.0)

def random_date_in_range() -> datetime:
    """Tire une date aléatoire, pondérée par la saisonnalité (rejet simple)."""
    while True:
        day_offset = random.randint(0, TOTAL_DAYS)
        candidate = START_DATE + timedelta(days=day_offset)
        if random.random() < seasonal_factor(candidate) / 1.8:
            hour = random.randint(8, 21)
            minute = random.randint(0, 59)
            return candidate.replace(hour=hour, minute=minute, second=0)

def pick_product():
    # Quelques produits plus populaires que d'autres
    weights = [3, 2, 3, 2, 2, 2, 2, 1, 2, 4, 4, 3, 2, 1]
    return random.choices(PRODUCTS, weights=weights, k=1)[0]

# ----------------------------------------------------------------------
# 2. SOURCE "SITE WEB" — JSON façon API REST
# Volume : ~3500 commandes
# ----------------------------------------------------------------------
web_orders = []
for i in range(1, 3501):
    p = pick_product()
    dt = random_date_in_range()
    qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
    # Petite variation de prix (promos occasionnelles)
    price = p["prix_reference"]
    if random.random() < 0.12:
        price = round(price * random.choice([0.85, 0.90, 0.95]))

    order = {
        "order_id": f"WEB-{dt.year}-{i:05d}",
        "product_id": p["product_id"],
        "product_name": p["nom"],
        "category": p["categorie"],
        "quantity": qty,
        "unit_price": price,
        "currency": "XAF",
        "channel": "website",
        "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "customer_id": f"C-{random.randint(1000, 9999)}"
    }
    web_orders.append(order)

    # ~2% de doublons volontaires (problème de fiabilité API à nettoyer)
    if random.random() < 0.02:
        web_orders.append(dict(order))

with open(RAW_DIR / "web_orders.json", "w", encoding="utf-8") as f:
    json.dump(web_orders, f, ensure_ascii=False, indent=2)

print(f"web_orders.json généré ({len(web_orders)} lignes, dont doublons volontaires)")

# ----------------------------------------------------------------------
# 3. SOURCE "POINTS DE VENTE PHYSIQUES" — CSV façon export caisse
# Schéma différent : date/heure séparées, ';' séparateur, libellés produit
# parfois légèrement différents (fautes/variantes), pas de devise explicite.
# Volume : ~2800 lignes
# ----------------------------------------------------------------------
MAGASINS = ["Magasin-Douala-01", "Magasin-Douala-02", "Magasin-Yaounde-01", "Magasin-Bafoussam-01"]
MODES_PAIEMENT = ["Mobile Money", "Cash", "Carte Bancaire", "Orange Money"]

# Quelques variantes de libellés pour simuler le bruit
NAME_VARIANTS = {
    "Casque Bluetooth XR-200": ["Casque Bluetooth XR-200", "Casque BT XR200", "casque bluetooth xr-200"],
    "Robe Wax Modèle Akwa": ["Robe Wax Modèle Akwa", "Robe Wax Akwa", "ROBE WAX AKWA"],
    "Huile de Coco Bio 500ml": ["Huile de Coco Bio 500ml", "Huile Coco Bio 500 ml"],
}

pos_rows = []
for i in range(1, 2801):
    p = pick_product()
    dt = random_date_in_range()
    qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
    price = p["prix_reference"]
    if random.random() < 0.08:
        price = round(price * random.choice([0.90, 0.95]))

    label = p["nom"]
    if label in NAME_VARIANTS and random.random() < 0.3:
        label = random.choice(NAME_VARIANTS[label])

    pos_rows.append({
        "date_vente": dt.strftime("%Y-%m-%d"),
        "heure": dt.strftime("%H:%M"),
        "magasin": random.choice(MAGASINS),
        "code_produit": p["product_id"],
        "libelle_produit": label,
        "qte": qty,
        "prix_unitaire": price,
        "mode_paiement": random.choice(MODES_PAIEMENT)
    })

# Quelques lignes avec quantité manquante (valeur vide) -> à nettoyer
for _ in range(15):
    row = random.choice(pos_rows)
    row["qte"] = ""

with open(RAW_DIR / "pos_sales.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["date_vente", "heure", "magasin", "code_produit",
                                            "libelle_produit", "qte", "prix_unitaire", "mode_paiement"],
                             delimiter=";")
    writer.writeheader()
    for row in pos_rows:
        writer.writerow(row)

print(f"pos_sales.csv généré ({len(pos_rows)} lignes, avec variantes de libellés et valeurs manquantes)")

# ----------------------------------------------------------------------
# 4. SOURCE "RÉSEAUX SOCIAUX" — SQLite, schéma bruité
# Prix en texte (avec devise mélangée), dates en format différent (DD/MM/YYYY),
# pas de category, quantity parfois en texte ("deux" au lieu de 2).
# Volume : ~1800 lignes
# ----------------------------------------------------------------------
db_path = RAW_DIR / "social_orders.db"
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE social_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref_commande TEXT,
        produit_id TEXT,
        produit_nom TEXT,
        quantite TEXT,
        prix TEXT,
        plateforme TEXT,
        date_commande TEXT,
        client_contact TEXT
    )
""")

PLATEFORMES = ["Instagram", "WhatsApp", "Facebook Shop", "TikTok Shop"]
QTY_TEXT_MAP = {1: "1", 2: "2", 3: "3", 4: "4"}

for i in range(1, 1801):
    p = pick_product()
    dt = random_date_in_range()
    qty = random.choices([1, 2, 3, 4], weights=[55, 25, 12, 8])[0]

    # Quantité parfois écrite en toutes lettres (bruit à nettoyer)
    if random.random() < 0.05:
        qty_str = {1: "un", 2: "deux", 3: "trois", 4: "quatre"}[qty]
    else:
        qty_str = str(qty)

    price = p["prix_reference"]
    if random.random() < 0.1:
        price = round(price * random.choice([0.85, 0.92]))

    # Prix formaté de façon hétérogène
    price_format = random.choice([
        f"{price} FCFA",
        f"{price}XAF",
        f"{price}",
        f"{price:,} FCFA".replace(",", " ")
    ])

    cur.execute("""
        INSERT INTO social_orders (ref_commande, produit_id, produit_nom, quantite, prix, plateforme, date_commande, client_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"SOC-{i:05d}",
        p["product_id"],
        p["nom"],
        qty_str,
        price_format,
        random.choice(PLATEFORMES),
        dt.strftime("%d/%m/%Y %H:%M"),
        f"+237 6{random.randint(70000000, 99999999)}"
    ))

conn.commit()
conn.close()

print("social_orders.db généré (1800 lignes, quantités/prix/dates en formats hétérogènes)")

print("\nGénération terminée. Fichiers dans:", OUT_DIR.resolve())
