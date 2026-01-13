# SECMAR - Application Streamlit

Application web de gestion des opérations de sauvetage maritime.

## Lancement

```bash
uv run streamlit run app/main.py
```

## Structure

```
app/
├── main.py              # Page d'accueil (KPIs, navigation)
├── pages/
│   ├── 1_Dashboard.py   # Tableau de bord analytique
│   ├── 2_Operations.py  # CRUD opérations
│   ├── 3_Schema.py      # Visualisation schéma BDD
│   └── 4_Audit.py       # Journal d'audit
└── components/
    ├── state.py         # Gestion état session
    ├── operations/      # Composants opérations
    ├── flotteurs/       # Composants flotteurs
    └── resultats/       # Composants résultats humains
```

## Pages

### main.py - Accueil
- Test de connexion base de données
- KPIs globaux (opérations, CROSS actifs, personnes impliquées)
- Navigation rapide

### 1_Dashboard.py - Tableau de bord
- Graphiques interactifs (Plotly)
- Distribution par CROSS et type d'opération
- Évolution temporelle
- Carte géographique
- Export CSV

### 2_Operations.py - Gestion des opérations
- Liste paginée avec filtres
- Vue détaillée par opération
- CRUD complet (opérations, flotteurs, résultats humains)

### 3_Schema.py - Schéma BDD
- Diagramme ER généré dynamiquement
- Documentation des tables et relations

### 4_Audit.py - Audit
- Historique des modifications
- Filtres par table, utilisateur, type d'opération
- Visualisation des diffs avant/après

## Authentification

L'application requiert une connexion. Trois rôles disponibles :
- **viewer** : lecture seule
- **editor** : lecture et modification
- **admin** : accès complet
