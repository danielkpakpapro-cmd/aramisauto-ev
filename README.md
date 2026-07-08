# Aramisauto — suivi de la proportion de véhicules électriques

Projet minimal, focalisé uniquement sur Aramisauto.

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt --break-system-packages
pip install -r requirements-scraping.txt --break-system-packages
playwright install chromium
```

## Utilisation

```bash
python scraper.py
```

Ça affiche un résumé dans le terminal et ajoute une ligne par marque dans
`data/historique.csv` (jamais écrasé — chaque exécution ajoute un nouvel
instantané horodaté).

Si le site a changé de structure et que le scraper ne trouve plus les
marques, relance en mode visible pour observer ce qui se passe :

```powershell
$env:SCRAPER_HEADLESS="0"; python scraper.py
```

## Dashboard

```bash
streamlit run dashboard.py
```

Affiche la proportion électrique par marque, et son évolution dans le
temps une fois plusieurs exécutions de `scraper.py` accumulées.

## Automatisation (suivi périodique)

Planifie `python scraper.py` via le Planificateur de tâches Windows (ou
`cron` sous Mac/Linux), par exemple une fois par jour. Chaque exécution
ajoute un instantané à `data/historique.csv`, ce qui alimente le graphique
d'évolution du dashboard.

## Comment ça marche

Le scraper (`scraper.py`) :
1. Charge `https://www.aramisauto.com/achat/` (catalogue complet)
2. Ouvre le panneau "Tous les filtres" → onglet "Marques"
3. Lit la liste affichée (`Peugeot (715)`, `Renault (471)`, ...)
4. Refait la même chose sur `https://www.aramisauto.com/achat/electrique/`
   (catalogue électrique uniquement)
5. Calcule la proportion électrique par marque et sauvegarde dans le CSV

Aucun clic sur un filtre "carburant" dynamique n'est nécessaire : les 2
URLs sont fixes, et le panneau "Marques" est identique sur les deux pages.
C'est ce qui rend l'approche robuste (comparé à une tentative précédente de
cliquer directement sur le filtre "Électrique", qui s'est révélée fragile
en mode automatisé).

## Partager le dashboard en ligne (Streamlit Community Cloud)

Pour qu'une autre personne consulte le dashboard à tout moment, sans rien
installer : le scraping reste local (sur ta machine, planifié), et seul le
dashboard est hébergé en ligne, connecté à un dépôt GitHub qui contient les
CSV de données.

### 1. Créer le dépôt GitHub (une seule fois)

```bash
git init
git add .
git commit -m "Premier commit"
git branch -M main
git remote add origin https://github.com/<ton-compte>/<ton-repo>.git
git push -u origin main
```

### 2. Déployer sur Streamlit Community Cloud (une seule fois)

1. Va sur https://share.streamlit.io et connecte-toi avec ton compte GitHub.
2. Clique sur "New app", choisis ton dépôt, la branche `main`, et le fichier
   principal `dashboard.py` (ou `dashboard_modeles.py` pour la version
   détaillée par modèle — tu peux déployer les deux comme deux apps
   séparées).
3. Déploie. Streamlit installera automatiquement les dépendances listées
   dans `requirements.txt` (volontairement sans Playwright — le dashboard
   n'en a pas besoin, seul le scraping local en a besoin).
4. Tu obtiens une URL du type `https://<ton-app>.streamlit.app` à partager.

### 3. Automatiser la mise à jour (scraping local + push GitHub)

Au lieu de planifier `python scraper.py` seul (voir plus haut), planifie
**`push_update.ps1`** à la place — il fait le scraping PUIS envoie le CSV
mis à jour sur GitHub :

Dans le Planificateur de tâches Windows :
- Programme/script : `powershell.exe`
- Arguments : `-ExecutionPolicy Bypass -File "C:\chemin\complet\vers\push_update.ps1"`

Streamlit Cloud redéploie automatiquement l'app à chaque push sur GitHub —
le dashboard en ligne se met donc à jour tout seul, quelques dizaines de
secondes après chaque exécution planifiée.

**Note** : le bouton "Lancer un scraping maintenant" du dashboard ne
fonctionne qu'en local (Playwright n'est pas installé sur Streamlit Cloud,
volontairement, pour garder le déploiement léger) — en ligne, le dashboard
affiche juste les données les plus récentes poussées depuis ta machine.


- Si Aramisauto change la structure de son site (nom des boutons,
  organisation du panneau de filtres), le scraper devra être ajusté —
  relance-le en mode visible (`SCRAPER_HEADLESS=0`) pour voir ce qui bloque.
- Pas de détail par modèle (uniquement par marque) : le site n'affichait
  pas de compteur par modèle dans le panneau observé. Si tu trouves un tel
  compteur en explorant le site, dis-le-moi et j'ajusterai le scraper.
- Reste raisonnable sur la fréquence des exécutions (pas plus d'une poignée
  de fois par jour), et vérifie les CGU du site pour un usage intensif ou
  commercial.