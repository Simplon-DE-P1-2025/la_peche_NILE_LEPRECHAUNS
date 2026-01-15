# src/analytics/ - Requetes Analytiques

> Requetes SQL et fonctions d'analyse pour les dashboards.

## But

Ce module centralise les requetes analytiques utilisees par les pages de dashboard et de KPIs. Il fournit des fonctions pretes a l'emploi pour les visualisations.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `queries.py` | Requetes analytiques pour les dashboards |

## Types de requetes

| Type | Description |
|------|-------------|
| **Agregations** | Comptages par CROSS, type d'operation, periode |
| **Tendances** | Evolution temporelle des operations |
| **KPIs** | Indicateurs de performance officiels |
| **Geographiques** | Repartition par zone, departement |

## Utilisation

```python
from src.analytics.queries import get_operations_by_cross

# Obtenir les operations par CROSS
df = get_operations_by_cross(session, year=2023)
```

## Lien avec les KPIs

Les requetes de ce module alimentent les pages :
- `1_Dashboard.py` : Graphiques generaux
- `6_KPI_Securite.py` : Indicateurs de securite
- `7_Performance_CROSS.py` : Performance des CROSS

## Dependances

- SQLAlchemy
- pandas
