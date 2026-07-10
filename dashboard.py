"""
dashboard.py — Aramisauto uniquement
======================================
Lit data/historique.csv (généré automatiquement chaque jour par GitHub
Actions, voir .github/workflows/scraping.yml) et affiche :
  - la proportion électrique par marque au dernier relevé,
  - l'évolution de cette proportion dans le temps.

Lancement :
    pip install streamlit pandas plotly --break-system-packages
    streamlit run dashboard.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

CSV_PATH = "data/historique.csv"

st.set_page_config(page_title="Aramisauto — proportion électrique", layout="wide")
st.title("🔋 Aramisauto — proportion de véhicules électriques par marque")

if not os.path.exists(CSV_PATH):
    st.warning(f"Aucune donnée trouvée ({CSV_PATH} n'existe pas encore). "
               f"Lance d'abord `python scraper.py` pour générer un premier relevé.")
    st.stop()

df = pd.read_csv(CSV_PATH, sep=None, engine="python")

# Conversion explicite et tolérante : si le fichier a un jour un mélange de
# séparateurs (ex: lignes ';' et ',' dans le même CSV), parse_dates peut
# échouer silencieusement et laisser la colonne en texte. On force la
# conversion ici et on avertit si certaines lignes ne sont pas exploitables.
df["date_releve"] = pd.to_datetime(df["date_releve"], errors="coerce")
n_invalid = df["date_releve"].isna().sum()
if n_invalid:
    st.warning(
        f"{n_invalid} ligne(s) du CSV ont une date illisible et ont été ignorées. "
        f"Cause probable : mélange de séparateurs ';' et ',' dans le fichier "
        f"(ex: fichier ouvert/modifié dans Excel à un moment). Si le problème "
        f"persiste, renomme data/historique.csv et relance `python scraper.py` "
        f"pour repartir sur un fichier propre."
    )
    df = df.dropna(subset=["date_releve"])
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
    text="nb_electrique",
)
fig.update_traces(texttemplate="%{text}", textposition="outside", textfont=dict(color="white", size=13))
fig.update_yaxes(tickformat=".0%", range=[0, latest["proportion_electrique"].max() * 1.15 + 0.05])
st.plotly_chart(fig, use_container_width=True)

st.subheader("Détail par marque")
st.dataframe(
    latest[["marque", "nb_total", "nb_electrique", "proportion_electrique"]]
    .style.format({"proportion_electrique": "{:.1%}"}),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# --- Détail par marque ET modèle (même format que le dashboard Ayvens, ---
# --- pour faciliter la comparaison entre sites) ---
st.subheader("Détail par marque et modèle")

MODELS_CSV_PATH = "data/historique_modeles.csv"
if not os.path.exists(MODELS_CSV_PATH):
    st.info(
        f"Pas encore de détail par modèle disponible ({MODELS_CSV_PATH} n'existe pas). "
        f"Lance `python scraper_modeles.py` pour le générer."
    )
else:
    df_models = pd.read_csv(MODELS_CSV_PATH, sep=None, engine="python")
    df_models["date_releve"] = pd.to_datetime(df_models["date_releve"], errors="coerce")
    df_models = df_models.dropna(subset=["date_releve"])

    if df_models.empty:
        st.info("Le fichier de détail par modèle est vide.")
    else:
        last_date_models = df_models["date_releve"].max()
        st.caption(f"Dernier relevé par modèle : {last_date_models.strftime('%d/%m/%Y %H:%M')}")

        detail = df_models[df_models["date_releve"] == last_date_models].copy()
        detail = detail[detail["nb_total"] > 0]

        col_f1, col_f2 = st.columns([2, 1])
        marques_modeles_dispo = sorted(detail["marque"].unique())
        selected_marques_modeles = col_f1.multiselect(
            "Filtrer par marque", marques_modeles_dispo, default=[], key="marque_filter_modeles"
        )
        only_electric_models = col_f2.checkbox("Uniquement modèles avec ≥1 électrique")

        if selected_marques_modeles:
            detail = detail[detail["marque"].isin(selected_marques_modeles)]
        if only_electric_models:
            detail = detail[detail["nb_electrique"] > 0]

        detail = detail.sort_values(["marque", "nb_total"], ascending=[True, False])

        st.dataframe(
            detail[["marque", "modele", "nb_total", "nb_electrique", "proportion_electrique"]]
            .rename(columns={
                "marque": "Marque", "modele": "Modèle", "nb_total": "Total",
                "nb_electrique": "Électrique", "proportion_electrique": "% Électrique",
            }).style
                .format({"% Électrique": "{:.1%}"}),
            use_container_width=True,
            hide_index=True,
            height=500,
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
st.caption("💡 Les données sont mises à jour automatiquement une fois par jour "
           "(GitHub Actions) — recharge la page pour voir la dernière version.")