"""
dashboard.py — Aramisauto uniquement
======================================
Lit data/historique.csv (genere par scraper.py) et affiche :
  - la proportion electrique par marque au dernier releve,
  - l'evolution de cette proportion dans le temps.

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

st.set_page_config(page_title="Aramisauto — proportion electrique", layout="wide")
st.title("Aramisauto — proportion de vehicules electriques par marque")

st.sidebar.header("Actualisation")

auto_refresh = st.sidebar.checkbox("Auto-actualiser l'affichage", value=False)
if auto_refresh:
    interval_min = st.sidebar.slider("Toutes les (minutes)", 1, 60, 5)
    st.sidebar.caption(
        "Relit simplement le CSV toutes les X minutes."
    )
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=interval_min * 60 * 1000, key="auto_refresh_timer")
    except ImportError:
        st.sidebar.warning(
            "Package manquant : pip install streamlit-autorefresh --break-system-packages"
        )

st.sidebar.divider()
st.sidebar.caption(
    "Scraping en direct (30s, par marque). Pour le detail par modele, "
    "lance python scraper_modeles.py separement (20-30 min)."
)

try:
    import playwright  # noqa: F401
    playwright_available = True
except ImportError:
    playwright_available = False

if not playwright_available:
    st.sidebar.info(
        "Scraping manuel indisponible ici (app deployee sans Playwright, "
        "volontairement, pour rester legere). Le scraping tourne en local "
        "sur ta machine et pousse les mises a jour via push_update.ps1."
    )
elif st.sidebar.button("Lancer un scraping maintenant"):
    with st.spinner("Scraping en cours (30 secondes)..."):
        result = subprocess.run(
            [sys.executable, "scraper.py"],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode == 0:
            st.sidebar.success("Termine !")
            with st.sidebar.expander("Details"):
                st.code(result.stdout)
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("Echec du scraping :")
            st.sidebar.code(result.stdout + "\n" + result.stderr)

if not os.path.exists(CSV_PATH):
    st.warning(f"Aucune donnee trouvee ({CSV_PATH}). Lance python scraper.py.")
    st.stop()

df = pd.read_csv(CSV_PATH, sep=None, engine="python")

df["date_releve"] = pd.to_datetime(df["date_releve"], errors="coerce")
n_invalid = df["date_releve"].isna().sum()
if n_invalid:
    st.warning(f"{n_invalid} ligne(s) ignoree(s) (date illisible).")
    df = df.dropna(subset=["date_releve"])
if df.empty:
    st.warning("Le fichier de donnees est vide.")
    st.stop()

last_date = df["date_releve"].max()
st.caption(f"Dernier releve : {last_date.strftime('%d/%m/%Y %H:%M')}")

latest = df[df["date_releve"] == last_date].copy()
latest = latest[latest["nb_total"] > 0].sort_values("nb_total", ascending=False)

col1, col2, col3 = st.columns(3)
total_vehicules = latest["nb_total"].sum()
total_electriques = latest["nb_electrique"].sum()
prop_globale = (total_electriques / total_vehicules) if total_vehicules else 0
col1.metric("Vehicules au catalogue", f"{total_vehicules:,}".replace(",", " "))
col2.metric("Dont electriques", f"{total_electriques:,}".replace(",", " "))
col3.metric("Proportion electrique globale", f"{prop_globale:.1%}")

st.divider()

st.subheader("Proportion electrique par marque (dernier releve)")
fig = px.bar(
    latest, x="marque", y="proportion_electrique",
    hover_data=["nb_total", "nb_electrique"],
    labels={"proportion_electrique": "% electrique", "marque": "Marque"},
)
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Detail par marque")
st.dataframe(
    latest[["marque", "nb_total", "nb_electrique", "proportion_electrique"]]
    .style.format({"proportion_electrique": "{:.1%}"}),
    use_container_width=True,
    hide_index=True,
)

st.divider()

st.subheader("Evolution dans le temps")
if df["date_releve"].nunique() <= 1:
    st.info("Un seul releve pour l'instant.")
else:
    marques_dispo = sorted(df.loc[df["nb_total"] > 0, "marque"].unique())
    selected = st.multiselect("Marques a afficher", marques_dispo, default=marques_dispo[:5])
    df_sel = df[df["marque"].isin(selected)] if selected else df
    fig_evo = px.line(df_sel, x="date_releve", y="proportion_electrique", color="marque", markers=True)
    fig_evo.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_evo, use_container_width=True)

st.divider()
st.caption("Deux facons d'avoir des donnees a jour : auto-actualisation ou bouton manuel (local uniquement).")
