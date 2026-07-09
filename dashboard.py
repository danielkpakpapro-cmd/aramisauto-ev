"""
dashboard.py - Aramisauto uniquement
Lit data/historique.csv, mis a jour automatiquement chaque jour par
GitHub Actions (voir .github/workflows/scraping.yml).
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

CSV_PATH = "data/historique.csv"

st.set_page_config(page_title="Aramisauto - proportion electrique", layout="wide")
st.title("Aramisauto - proportion de vehicules electriques par marque")

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
st.caption("Les donnees sont mises a jour automatiquement une fois par jour (GitHub Actions).")
