# app/components/ - Composants UI Reutilisables

> Composants Streamlit reutilisables pour les formulaires et listes.

## But

Ce module contient les composants d'interface utilisateur partages entre les pages. Il permet de factoriser le code des formulaires et listes pour les differentes entites.

## Structure

```
components/
├── state.py         # Gestion de l'etat session Streamlit
├── operations/      # Composants pour les operations
│   ├── detail.py    # Vue detaillee d'une operation
│   ├── form.py      # Formulaire creation/edition
│   └── list.py      # Liste des operations
├── flotteurs/       # Composants pour les flotteurs
│   ├── form.py      # Formulaire flotteur
│   └── list.py      # Liste des flotteurs
└── resultats/       # Composants pour les resultats humains
    ├── form.py      # Formulaire resultat humain
    └── list.py      # Liste des resultats
```

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `state.py` | Initialisation et gestion de l'etat session Streamlit |

## Sous-dossiers

### operations/

| Fichier | Description |
|---------|-------------|
| `detail.py` | Affichage detaille d'une operation avec ses flotteurs et resultats |
| `form.py` | Formulaire de creation/edition d'operation |
| `list.py` | Liste paginee des operations avec filtres |

### flotteurs/

| Fichier | Description |
|---------|-------------|
| `form.py` | Formulaire de creation/edition de flotteur |
| `list.py` | Liste des flotteurs d'une operation |

### resultats/

| Fichier | Description |
|---------|-------------|
| `form.py` | Formulaire de creation/edition de resultat humain |
| `list.py` | Liste des resultats humains d'une operation |

## Utilisation

```python
from app.components.operations.list import render_operations_list
from app.components.operations.form import render_operation_form

# Afficher la liste des operations
render_operations_list(session)

# Afficher le formulaire d'edition
render_operation_form(session, operation_id=123)
```

## Lien avec src/schema/

Ces composants utilisent le framework de generation de formulaires defini dans `src/schema/` pour generer automatiquement les champs et la validation.
