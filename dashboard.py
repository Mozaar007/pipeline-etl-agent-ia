"""
dashboard.py — Dashboard Streamlit pour visualisation des ventes et rapport IA.

Lit directement l'entrepôt DuckDB (vues agrégées) et le dernier rapport
d'insights généré par l'agent IA, et les affiche dans une interface web.

Usage :
    streamlit run dashboard.py
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "warehouse.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

st.set_page_config(
    page_title="Pipeline ETL — Analyse des Ventes",
    page_icon="📊",
    layout="wide"
)

# ----------------------------------------------------------------------
# CHARGEMENT DES DONNÉES
# ----------------------------------------------------------------------
@st.cache_data(ttl=300)  # cache 5 minutes
def load_data():
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    by_month    = conn.execute("SELECT * FROM v_sales_by_month").df()
    by_product  = conn.execute("SELECT * FROM v_sales_by_product").df()
    by_category = conn.execute("SELECT * FROM v_sales_by_category").df()
    by_channel  = conn.execute("SELECT * FROM v_sales_by_channel").df()
    conn.close()
    return by_month, by_product, by_category, by_channel


def load_latest_report() -> dict | None:
    """Charge le dernier rapport JSON généré par l'agent IA."""
    json_files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    if not json_files:
        return None
    with open(json_files[0], "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# UTILITAIRES
# ----------------------------------------------------------------------
def fmt_xaf(value: float) -> str:
    """Formate un montant en XAF lisible (ex: 165 623 000 XAF)."""
    return f"{value:,.0f} XAF".replace(",", " ")

def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------
st.title("📊 Pipeline ETL Intelligent — Analyse des Ventes")
st.markdown(
    "Dashboard alimenté par le pipeline ETL (Python · DuckDB · Prefect) "
    "et enrichi par un agent IA (Claude API)."
)
st.divider()

# Chargement
try:
    by_month, by_product, by_category, by_channel = load_data()
except Exception as e:
    st.error(f"Impossible de se connecter à l'entrepôt DuckDB : {e}")
    st.stop()

# ----------------------------------------------------------------------
# KPIs GLOBAUX
# ----------------------------------------------------------------------
total_revenue  = by_channel["total_revenue"].sum()
total_margin   = by_channel["total_margin"].sum()
total_orders   = by_channel["nb_orders"].sum()
total_qty      = by_channel["total_quantity"].sum()
margin_rate    = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Revenue total",    fmt_xaf(total_revenue))
col2.metric("📈 Marge totale",     fmt_xaf(total_margin))
col3.metric("🎯 Taux de marge",    fmt_pct(margin_rate))
col4.metric("🛒 Nb commandes",     f"{int(total_orders):,}".replace(",", " "))

st.divider()

# ----------------------------------------------------------------------
# TENDANCES MENSUELLES
# ----------------------------------------------------------------------
st.subheader("📅 Tendances mensuelles")

fig_month = go.Figure()
fig_month.add_trace(go.Bar(
    x=by_month["year_month"],
    y=by_month["total_revenue"],
    name="Revenue",
    marker_color="#2563EB",
    opacity=0.85
))
fig_month.add_trace(go.Scatter(
    x=by_month["year_month"],
    y=by_month["total_margin"],
    name="Marge",
    mode="lines+markers",
    line=dict(color="#16A34A", width=2.5),
    marker=dict(size=6)
))
fig_month.update_layout(
    xaxis_title="Mois",
    yaxis_title="Montant (XAF)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    height=380
)
st.plotly_chart(fig_month, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# TOP PRODUITS + CANAUX/CATÉGORIES
# ----------------------------------------------------------------------
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🏆 Top produits par revenue")
    top10 = by_product.head(10).sort_values("total_revenue")
    fig_prod = px.bar(
        top10,
        x="total_revenue",
        y="product_name",
        orientation="h",
        color="category",
        labels={"total_revenue": "Revenue (XAF)", "product_name": "Produit", "category": "Catégorie"},
        height=380,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_prod.update_layout(showlegend=True)
    st.plotly_chart(fig_prod, use_container_width=True)

with col_right:
    st.subheader("📡 Revenue par canal")
    fig_channel = px.pie(
        by_channel,
        values="total_revenue",
        names="channel",
        hole=0.45,
        height=180,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_channel.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
    st.plotly_chart(fig_channel, use_container_width=True)

    st.subheader("🗂️ Revenue par catégorie")
    fig_cat = px.pie(
        by_category,
        values="total_revenue",
        names="category",
        hole=0.45,
        height=180,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_cat.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
    st.plotly_chart(fig_cat, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# RAPPORT AGENT IA
# ----------------------------------------------------------------------
st.subheader("🤖 Rapport Agent IA (dernière analyse)")

report = load_latest_report()

if report is None:
    st.info("Aucun rapport IA disponible. Lance `python pipeline.py --mock` pour en générer un.")
else:
    st.markdown(f"**Période analysée :** {report.get('periode_analysee', '')}")
    st.markdown(f"> {report.get('resume_executif', '')}")

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("**🏆 Top produits**")
        for p in report.get("top_produits", []):
            st.markdown(
                f"- **{p['produit']}** — {p['revenue']:,.0f} XAF  \n"
                f"  _{p['commentaire']}_"
            )

        st.markdown("**📅 Tendances temporelles**")
        tt = report.get("tendances_temporelles", {})
        st.markdown(tt.get("observation_principale", ""))
        if "pic" in tt:
            st.markdown(f"- 🔺 **Pic** ({tt['pic'].get('periode','')}) : {tt['pic'].get('detail','')}")
        if "creux" in tt:
            st.markdown(f"- 🔻 **Creux** ({tt['creux'].get('periode','')}) : {tt['creux'].get('detail','')}")

    with col_r2:
        st.markdown("**⚠️ Anomalies détectées**")
        for a in report.get("anomalies_detectees", []):
            st.markdown(f"- {a}")

        st.markdown("**✅ Recommandations**")
        for i, r in enumerate(report.get("recommandations", []), 1):
            st.markdown(f"{i}. {r}")

st.divider()
st.caption("Pipeline ETL Intelligent · BigIcks Consulting · Données générées à des fins de démonstration")