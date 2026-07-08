"""
dashboard.py — Aramisauto uniquement
======================================
Lit data/historique.csv (généré par scraper.py) et affiche :
  - la proportion électrique par marque au dernier relevé,
  - l'évolution de cette proportion dans le temps (une fois plusieurs
    exécutions de scraper.py accumulées).

Lancement :
    pip install streamlit pandas plotly --break-system-packages
    streamlit run dashboard.py
"""

import os
import subprocess
import sys
import time

import pandas as pd
import plotly.express as px
import streamlit as st

CSV_PATH = "data/historique.csv"

st.set_page_config(page_title="Aramisauto — proportion électrique", layout="wide")
st.title("🔋 Aramisauto — proportion de véhicules électriques par marque")

# --- Barre latérale : actualisation ---
st.sidebar.header("Actualisation")

auto_refresh = st.sidebar.checkbox("Auto-actualiser l'affichage", value=False)
if auto_refresh:
    interval_min = st.sidebar.slider("Toutes les (minutes)", 1, 60, 5)
    st.sidebar.caption(
        "Relit simplement le CSV toutes les X minutes — utile si un scraping "
        "tourne en tâche planifiée en arrière-plan et met à jour le fichier."
    )
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=interval_min * 60 * 1000, key="auto_refresh_timer")
    except ImportError:
        st.sidebar.warning(
            "Package manquant pour l'auto-actualisation : "
            "`pip install streamlit-autorefresh --break-system-packages` puis relance."
        )

st.sidebar.divider()
st.sidebar.caption(
    "Scraping en direct (≈30s, par marque uniquement). Pour le détail par "
    "modèle, lance `python scraper_modeles.py` séparément (20-30 min, trop "
    "long pour un bouton dans l'app)."
)
if st.sidebar.button("🔄 Lancer un scraping maintenant"):
    with st.spinner("Scraping en cours (≈30 secondes)..."):
        result = subprocess.run(
            [sys.executable, "scraper.py"],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode == 0:
            st.sidebar.success("Terminé !")
            with st.sidebar.expander("Détails"):
                st.code(result.stdout)
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("Échec du scraping — détails ci-dessous :")
            st.sidebar.code(result.stdout + "\n" + result.stderr)

if not os.path.exists(CSV_PATH):
    st.warning(f"Aucune donnée trouvée ({CSV_PATH} n'existe pas encore). "
               f"Lance d'abord `python scraper.py` pour générer un premier relevé.")
    st.stop()

df = pd.read_csv(CSV_PATH, parse_dates=["date_releve"], sep=None, engine="python")
if df.empty:
    st.warning("Le fichier de données est vide.")
    st.stop()

last_date = df["date_releve"].max()
st.caption(f"Dernier relevé : {last_date.strftime('%d/%m/%Y %H:%M')}")

latest = df[df["date_releve"] == last_date].copy()
latest = latest[latest["nb_total"] > 0].sort_values("nb_total", ascending=False)

# --- KPI globaux ---
col1, col2, col3 = st.columns(3)
total_vehicules = latest["nb_total"].sum()
total_electriques = latest["nb_electrique"].sum()
prop_globale = (total_electriques / total_vehicules) if total_vehicules else 0
col1.metric("Véhicules au catalogue", f"{total_vehicules:,}".replace(",", " "))
col2.metric("Dont électriques", f"{total_electriques:,}".replace(",", " "))
col3.metric("Proportion électrique globale", f"{prop_globale:.1%}")

st.divider()

# --- Proportion par marque (dernier relevé) ---
st.subheader("Proportion électrique par marque (dernier relevé)")
fig = px.bar(
    latest, x="marque", y="proportion_electrique",
    hover_data=["nb_total", "nb_electrique"],
    labels={"proportion_electrique": "% électrique", "marque": "Marque"},
)
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Détail par marque")
st.dataframe(
    latest[["marque", "nb_total", "nb_electrique", "proportion_electrique"]]
    .style.format({"proportion_electrique": "{:.1%}"}),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# --- Évolution dans le temps ---
st.subheader("Évolution dans le temps")
if df["date_releve"].nunique() <= 1:
    st.info("Un seul relevé pour l'instant — relance `python scraper.py` plusieurs fois "
            "(idéalement via une tâche planifiée) pour voir l'évolution ici.")
else:
    marques_dispo = sorted(df.loc[df["nb_total"] > 0, "marque"].unique())
    selected = st.multiselect("Marques à afficher", marques_dispo, default=marques_dispo[:5])
    df_sel = df[df["marque"].isin(selected)] if selected else df
    fig_evo = px.line(df_sel, x="date_releve", y="proportion_electrique", color="marque", markers=True)
    fig_evo.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_evo, use_container_width=True)

st.divider()
st.caption("💡 Deux façons d'avoir des données à jour : (1) coche 'Auto-actualiser l'affichage' "
           "dans la barre latérale si un scraping tourne en tâche planifiée en arrière-plan, "
           "ou (2) clique sur 'Lancer un scraping maintenant' pour un relevé immédiat "
           "(≈30 secondes, marque uniquement).")