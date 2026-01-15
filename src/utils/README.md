# src/utils/ - Utilitaires SECMAR

> Fonctions utilitaires pour la performance, les filtres DataFrame et le pre-chargement.

## But

Ce module contient des utilitaires transversaux utilises par l'application Streamlit et le code metier :
- Diagnostic et mesure de performance
- Filtrage in-memory des DataFrames
- Pre-chargement des caches au demarrage

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `performance.py` | Mesure de latence BDD, benchmark des requetes |
| `dataframe_filters.py` | Filtres et calculs KPI sur DataFrames Pandas |
| `warmload.py` | Pre-chargement des caches Streamlit au demarrage |

## performance.py

Outils de diagnostic et mesure de performance pour la base de donnees :
- `measure_db_latency()` : Mesure la latence reseau vers PostgreSQL
- `benchmark_dashboard_queries()` : Benchmark des requetes du Dashboard
- `PerformanceResults` : Dataclass avec les resultats complets

```python
from src.utils.performance import measure_db_latency, benchmark_dashboard_queries

# Mesurer la latence DB
latency = measure_db_latency(iterations=10)
print(f"Latence moyenne: {latency['avg_ms']:.2f}ms")

# Benchmarker les requetes du Dashboard
results = benchmark_dashboard_queries()
for r in results.queries:
    print(f"{r['name']}: {r['first_ms']:.2f}ms (sans cache)")
```

## dataframe_filters.py

Filtrage in-memory avec Pandas - instantane :

| Fonction | Description | Performance |
|----------|-------------|-------------|
| `filter_by_dates()` | Filtre par plage de dates | ~10ms |
| `filter_by_cross()` | Filtre par CROSS selectionnes | ~5ms |
| `filter_by_type()` | Filtre par type d'operation | ~5ms |
| `compute_kpis()` | Calcule les KPIs globaux | ~50ms |
| `compute_by_cross()` | Agregation par CROSS | ~50ms |
| `compute_by_type()` | Agregation par type | ~50ms |
| `compute_timeline()` | Agregation temporelle | ~100ms |
| `compute_yearly_stats()` | Statistiques annuelles | ~50ms |
| `compute_bilan_humain()` | Bilan des personnes | ~50ms |

```python
from src.utils.dataframe_filters import (
    filter_by_dates,
    filter_by_cross,
    compute_kpis,
    compute_timeline,
)

# Charger les donnees une fois (cachees)
df = get_operations_base()

# Filtrer en memoire (instantane)
df_filtered = filter_by_dates(df, date_debut, date_fin)
df_filtered = filter_by_cross(df_filtered, selected_cross)

# Calculer les agregats
kpis = compute_kpis(df_filtered)
timeline = compute_timeline(df_filtered, granularity='month')
```

## warmload.py

Pre-chargement des caches critiques au demarrage :

```python
from src.utils.warmload import warmload_critical_caches

# Au demarrage de l'application
warmload_critical_caches(verbose=True)
```

## Lien avec les autres modules

- **database/** : Les utilitaires utilisent les connexions et requetes de base
- **app/pages/** : Les pages utilisent les filtres DataFrame pour l'interactivite
- **app/pages/11_Diagnostic.py** : Page dediee utilisant `performance.py`

## Dependances

- pandas
- sqlalchemy
- streamlit
