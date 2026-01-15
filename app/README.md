# app/ - Application Streamlit SECMAR

> Application web de gestion des operations de sauvetage maritime.

## Lancement

```bash
uv run streamlit run app/main.py
```

## Structure

```
app/
├── main.py              # Page d'accueil (KPIs, navigation)
├── app.py               # Configuration Streamlit
├── pages/               # Pages de l'application
│   ├── 1_Dashboard.py   # Tableau de bord analytique
│   ├── 2_Operations.py  # CRUD operations
│   ├── 3_Schema.py      # Visualisation schema BDD
│   ├── 4_Audit.py       # Journal d'audit
│   ├── 5_Catalogue.py   # Catalogue de donnees
│   ├── 6_KPI_Securite.py        # KPIs securite maritime
│   ├── 7_Performance_CROSS.py   # Performance des CROSS
│   ├── 8_Analyse_Flotteurs.py   # Analyse des flotteurs
│   ├── 9_Saisonnalite_Meteo.py  # Saisonnalite et meteo
│   └── 10_Alertes_Anomalies.py  # Alertes et anomalies
└── components/          # Composants reutilisables
    ├── state.py         # Gestion etat session
    ├── operations/      # Composants operations
    ├── flotteurs/       # Composants flotteurs
    └── resultats/       # Composants resultats humains
```

## Pages

### main.py - Accueil
- Test de connexion base de donnees
- KPIs globaux (operations, CROSS actifs, personnes impliquees)
- Navigation rapide

### 1_Dashboard.py - Tableau de bord
- Graphiques interactifs (Plotly)
- Distribution par CROSS et type d'operation
- Evolution temporelle
- Carte geographique
- Export CSV

### 2_Operations.py - Gestion des operations
- Liste paginee avec filtres
- Vue detaillee par operation
- CRUD complet (operations, flotteurs, resultats humains)

### 3_Schema.py - Schema BDD
- Diagramme ER genere dynamiquement
- Documentation des tables et relations

### 4_Audit.py - Audit
- Historique des modifications
- Filtres par table, utilisateur, type d'operation
- Visualisation des diffs avant/apres

### 5_Catalogue.py - Catalogue de donnees
- Documentation des colonnes et types
- Dictionnaire de donnees

### 6_KPI_Securite.py - KPIs Securite
- Taux de succes des interventions
- Personnes secourues/decedees
- Indicateurs officiels Programme 205

### 7_Performance_CROSS.py - Performance CROSS
- Temps de reponse moyen
- Nombre d'operations par CROSS
- Comparaison inter-CROSS

### 8_Analyse_Flotteurs.py - Analyse Flotteurs
- Repartition par type de flotteur
- Resultats par categorie
- Tendances

### 9_Saisonnalite_Meteo.py - Saisonnalite et Meteo
- Operations par mois/saison
- Impact des conditions meteorologiques
- Correlation vent/mer

### 10_Alertes_Anomalies.py - Alertes et Anomalies
- Detection d'anomalies dans les donnees
- Alertes configurables
- Qualite des donnees

## Authentification

L'application requiert une connexion. Trois roles disponibles :

| Role | Droits |
|------|--------|
| `viewer` | Lecture seule |
| `editor` | Lecture et modification |
| `admin` | Acces complet |

## Composants

Voir [components/README.md](components/README.md) pour la documentation des composants reutilisables.
