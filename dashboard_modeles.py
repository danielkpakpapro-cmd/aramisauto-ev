"""
dashboard_modeles.py — Aramisauto, tableau détaillé par marque/modèle
========================================================================
Lit data/historique_modeles.csv (généré par scraper_modeles.py) et affiche
un tableau filtrable/triable : marque, modèle, total, électrique, proportion.

Lancement :
    streamlit run dashboard_modeles.py
"""

import os

import pandas as pd
import streamlit as st

CSV_PATH = "data/historique_modeles.csv"

st.set_page_config(page_title="Aramisauto — détail par modèle", layout="wide")
st.title("🔋 Aramisauto — proportion électrique par marque et modèle")

if not os.path.exists(CSV_PATH):
    st.warning(f"Aucune donnée trouvée ({CSV_PATH} n'existe pas encore). "
               f"Lance d'abord `python scraper_modeles.py`.")
    st.stop()

df = pd.read_csv(CSV_PATH, sep=None, engine="python")
df["date_releve"] = pd.to_datetime(df["date_releve"], errors="coerce")
n_invalid = df["date_releve"].isna().sum()
if n_invalid:
    st.warning(
        f"{n_invalid} ligne(s) ignorée(s) (date illisible, probablement un mélange "
        f"de séparateurs ';'/',' dans le fichier). Renomme data/historique_modeles.csv "
        f"et relance `python scraper_modeles.py` si le problème persiste."
    )
    df = df.dropna(subset=["date_releve"])
if df.empty:
    st.warning("Le fichier de données est vide.")
    st.stop()

last_date = df["date_releve"].max()
st.caption(f"Dernier relevé : {last_date.strftime('%d/%m/%Y %H:%M')}")

latest = df[df["date_releve"] == last_date].copy()
latest = latest[latest["nb_total"] > 0]

# --- Filtres ---
col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
marques = sorted(latest["marque"].unique())
selected_marques = col_f1.multiselect("Filtrer par marque", marques, default=[])
only_electric = col_f2.checkbox("Uniquement les modèles avec au moins 1 électrique")
sort_by = col_f3.selectbox("Trier par", ["proportion_electrique", "nb_total", "nb_electrique", "marque"])

view = latest.copy()
if selected_marques:
    view = view[view["marque"].isin(selected_marques)]
if only_electric:
    view = view[view["nb_electrique"] > 0]

view = view.sort_values(sort_by, ascending=(sort_by == "marque"))

# --- KPI ---
col1, col2, col3 = st.columns(3)
col1.metric("Modèles affichés", len(view))
col2.metric("Véhicules (vue filtrée)", f"{view['nb_total'].sum():,}".replace(",", " "))
prop = view["nb_electrique"].sum() / view["nb_total"].sum() if view["nb_total"].sum() else 0
col3.metric("Proportion électrique (vue filtrée)", f"{prop:.1%}")

st.divider()

# --- Tableau principal ---
st.subheader("Détail marque / modèle")
display_df = view[["marque", "modele", "nb_total", "nb_electrique", "proportion_electrique"]].rename(
    columns={
        "marque": "Marque",
        "modele": "Modèle",
        "nb_total": "Total",
        "nb_electrique": "Électrique",
        "proportion_electrique": "% Électrique",
    }
)

st.dataframe(
    display_df.style
        .format({"% Électrique": "{:.1%}"})
        .background_gradient(subset=["% Électrique"], cmap="Greens", vmin=0, vmax=1)
        .bar(subset=["Total"], color="#d0e6ff"),
    use_container_width=True,
    hide_index=True,
    height=600,
)

st.caption(
    f"{len(view)} lignes affichées sur {len(latest)} au total. "
    f"Utilise les filtres ci-dessus pour te concentrer sur certaines marques, "
    f"ou ne voir que les modèles ayant déjà au moins une version électrique."
)

st.divider()
st.download_button(
    "📥 Télécharger ce tableau en CSV",
    data=display_df.to_csv(index=False).encode("utf-8"),
    file_name="aramisauto_marque_modele.csv",
    mime="text/csv",
)