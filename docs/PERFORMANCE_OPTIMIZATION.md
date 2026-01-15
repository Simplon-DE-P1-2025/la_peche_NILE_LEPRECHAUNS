# Optimisation des Performances - SECMAR Dashboard

## Contexte

L'application SECMAR est un dashboard Streamlit connecté à une base PostgreSQL hébergée sur **Render.com**. La base contient **385 782 opérations** de sauvetage maritime avec des tables associées (flotteurs, résultats humains).

### Problème initial

- **Temps de chargement initial** : ~43 secondes
- **Latence réseau** : ~87-115ms (serveur distant)
- **Requêtes lentes** : Certaines requêtes prenaient jusqu'à 12 secondes

---

## Méthodologie de Diagnostic

### Outil de diagnostic créé

Fichier : `src/utils/performance.py`

```python
def benchmark_dashboard_queries() -> PerformanceResults:
    """Benchmark toutes les requêtes utilisées par le Dashboard."""
```

Cet outil mesure :
- La latence réseau vers la base de données
- Le temps d'exécution de chaque requête (avec et sans cache Streamlit)
- Le nombre de lignes retournées
- L'efficacité du cache

### Métriques clés analysées

| Métrique | Description |
|----------|-------------|
| `first_ms` | Temps sans cache (première exécution) |
| `cached_ms` | Temps avec cache Streamlit |
| `rows_returned` | Volume de données |
| `db_latency_avg_ms` | Latence réseau moyenne |

---

## Phases d'Optimisation

### Phase 1 : Vue Matérialisée `operations_stats`

**Problème identifié** : Le calcul des statistiques par opération (personnes secourues, décédées, etc.) nécessitait des JOINs complexes avec la table `resultats_humain` à chaque requête.

**Solution** : Création d'une vue matérialisée pré-calculant les métriques SECMAR officielles.

```sql
CREATE MATERIALIZED VIEW operations_stats AS
SELECT
    o.operation_id,
    -- Métriques officielles SECMAR (Programme 205)
    COALESCE(SUM(CASE WHEN rh.resultat_humain IN (
        'Personne secourue', 'Personne assistée', 'Personne retrouvée'
    ) THEN rh.nombre ELSE 0 END), 0)::INTEGER as nombre_saines_sauves,
    -- ... autres métriques
FROM operations o
LEFT JOIN resultats_humain rh ON o.operation_id = rh.operation_id
GROUP BY o.operation_id;
```

**Résultat** : 88s → 43s (**51% de gain**)

---

### Phase 2 : Vues Matérialisées KPI + Filtrage In-Memory

**Problème identifié** : Les fonctions KPI globales utilisaient `COUNT(DISTINCT)` qui forçait un tri sur disque (external merge sort).

**Solutions** :

#### 2.1 Vue `v_kpi_global`
```sql
CREATE MATERIALIZED VIEW v_kpi_global AS
SELECT
    COUNT(*) as total_operations,
    COUNT(DISTINCT o."cross") as nb_cross,
    COALESCE(SUM(s.nombre_impliques), 0) as total_personnes,
    -- ... autres agrégats
FROM operations o
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id;
```

#### 2.2 Vue `v_kpi_annuel`
```sql
CREATE MATERIALIZED VIEW v_kpi_annuel AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER as annee,
    COUNT(*)::INTEGER as total_operations,
    -- ... agrégats par année
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte);
```

#### 2.3 Vue `v_kpi_cross`
```sql
CREATE MATERIALIZED VIEW v_kpi_cross AS
SELECT
    COALESCE(o."cross", 'Non renseigné') as cross_name,
    COUNT(*)::INTEGER as total_operations,
    -- ... agrégats par CROSS
GROUP BY COALESCE(o."cross", 'Non renseigné');
```

#### 2.4 Filtrage In-Memory avec Pandas

Fichier : `src/utils/dataframe_filters.py`

```python
def filter_by_dates(df, date_debut, date_fin):
    """Filtre par plage de dates (instantané en mémoire)."""

def filter_by_cross(df, cross, cross_actifs_only):
    """Filtre par CROSS (instantané en mémoire)."""

def compute_kpis(df):
    """Calcule les KPIs depuis un DataFrame filtré."""
```

**Stratégie** : Charger les données de base une fois, puis filtrer en mémoire.

**Résultat** :
- `get_kpis` : 12.6s → 10ms (**99% de gain**)
- Changement de filtre : 2-5s → 50-200ms (**95% de gain**)

---

### Phase 3 : Optimisation YoY et Données de Base

**Problèmes identifiés** :
1. `get_kpi_yoy_latest` : 6.9s pour 1 ligne (CTE complexe avec fonctions window)
2. `get_operations_base` : 19.4s pour charger 385K lignes

**Solutions** :

#### 3.1 Vue `v_kpi_yoy_cross_actifs`

Pré-calcul des comparatifs Year-over-Year avec fonctions `LAG()` :

```sql
CREATE MATERIALIZED VIEW v_kpi_yoy_cross_actifs AS
WITH yearly_stats AS (
    SELECT
        EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
        COUNT(*)::INTEGER AS nb_operations,
        -- ... agrégats
    FROM operations o
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    WHERE o."cross" IN ('Antilles-Guyane', 'Corse', 'Corsen', ...)
    GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
)
SELECT
    y.annee,
    y.nb_operations,
    LAG(y.nb_operations) OVER (ORDER BY y.annee) AS ops_annee_precedente,
    ROUND((y.nb_operations - LAG(y.nb_operations) OVER (ORDER BY y.annee))::NUMERIC /
          NULLIF(LAG(y.nb_operations) OVER (ORDER BY y.annee), 0) * 100, 2) AS yoy_operations_pct,
    -- ... autres calculs YoY
FROM yearly_stats y;
```

#### 3.2 Limitation temporelle des données (ou date de départ explicite)

Améliorations associées :
- Chargement direct en DataFrame via `read_sql_query`
- Cache `@st.cache_resource` (évite la sérialisation)
- Dashboard configuré pour démarrer au 01/01/2020

```python
@st.cache_resource(ttl=3600)
def get_operations_base(years_back: int = 3, start_date: date | None = None) -> pd.DataFrame:
    """Charge les opérations récentes (ou depuis une date de départ)."""
    # start_date est prioritaire sur years_back
    sql = """
    SELECT ...
    FROM operations o
    WHERE o.date_heure_reception_alerte >= :start_date
    """
```

**Résultat** :
- `get_kpi_yoy_latest` : 6940ms → 109ms (**98% de gain**)
- `get_operations_base` : 19378ms → 4914ms (**75% de gain**)

---

### Phase 4 : Pages KPI Flotteurs & Performance CROSS

**Problèmes identifiés** :
- Page "Analyse Flotteurs" : JOIN 3 tables + GROUP BY à chaque requête
- Page "Performance CROSS" : Fonctions `PERCENTILE_CONT` et `RANK()` coûteuses

**Solutions** :

#### 4.1 Vue `v_kpi_cross_benchmark_mv`

```sql
CREATE MATERIALIZED VIEW v_kpi_cross_benchmark_mv AS
SELECT
    o."cross" as cross_name,
    COUNT(*)::INTEGER as nb_operations,
    ROUND(COALESCE(SUM(s.nombre_saines_sauves), 0)::NUMERIC /
          NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
    RANK() OVER (ORDER BY COUNT(*) DESC) as rank_volume,
    RANK() OVER (ORDER BY ... DESC) as rank_sauvetage
FROM operations o
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
GROUP BY o."cross";
```

#### 4.2 Vue `v_kpi_flotteurs_categorie_mv`

```sql
CREATE MATERIALIZED VIEW v_kpi_flotteurs_categorie_mv AS
SELECT
    f.categorie_flotteur,
    COUNT(DISTINCT f.operation_id)::INTEGER as total_operations,
    COUNT(*)::INTEGER as total_flotteurs,
    -- ... agrégats
FROM flotteurs f
JOIN operations o ON f.operation_id = o.operation_id
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
GROUP BY f.categorie_flotteur;
```

**Résultat attendu** :
- Page Performance CROSS : ~2-3s → ~100ms
- Page Analyse Flotteurs : ~2-3s → ~100ms

---

## Récapitulatif des Gains

### Évolution globale

| Métrique | Initial | Final | Gain |
|----------|---------|-------|------|
| **Temps total sans cache** | 27 624ms | ~6 000ms | **78%** |
| **Temps total avec cache** | 685ms | 123ms | **82%** |
| **Premier chargement** | ~43s | ~6s | **86%** |

### Détail par requête

| Requête | Avant | Après | Gain |
|---------|-------|-------|------|
| `get_kpis_global` | 12 600ms | 91ms | **99%** |
| `get_kpi_yoy_latest` | 6 940ms | 109ms | **98%** |
| `get_operations_base` | 19 378ms | 4 914ms | **75%** |
| `get_yearly_stats_cached` | 8 500ms | 96ms | **99%** |
| `get_cross_stats_cached` | 8 300ms | 97ms | **99%** |

---

## Architecture Finale

### Vues Matérialisées Créées

Vue utilitaire:
- `v_cross_actifs` : liste centralisée des CROSS actifs (utilisée par les vues matérialisées CROSS actifs)

| Vue | Objectif | Index |
|-----|----------|-------|
| `operations_stats` | Stats par opération (source) | `operation_id` |
| `v_kpi_global` | KPIs globaux agrégés | - |
| `v_kpi_annuel` | Stats par année | `annee` |
| `v_kpi_cross` | Stats par CROSS | `cross_name` |
| `v_kpi_yoy_cross_actifs` | Comparatifs YoY CROSS actifs | `annee` |
| `v_kpi_cross_benchmark_mv` | Benchmark performance CROSS | `cross_name` |
| `v_kpi_flotteurs_categorie_mv` | Stats flotteurs par catégorie | `categorie_flotteur` |
| `v_kpi_flotteurs_categorie_cross_actifs_mv` | Stats flotteurs (CROSS actifs) | `categorie_flotteur` |
| `v_kpi_flotteurs_analyse_cross_actifs_mv` | Flotteurs détaillés (CROSS actifs) | `type_flotteur, categorie_flotteur, resultat_flotteur` |
| `v_kpi_alertes_anomalies_mv` | Alertes et z-scores mensuels | `periode` |
| `v_kpi_alertes_anomalies_cross_actifs_mv` | Alertes mensuelles (CROSS actifs) | `periode` |
| `v_kpi_securite_mensuel_mv` | Sécurité mensuelle pré-calculée | `periode` |
| `v_kpi_securite_mensuel_cross_actifs_mv` | Sécurité mensuelle (CROSS actifs) | `periode` |
| `v_kpi_saisonnalite_mensuelle_cross_actifs_mv` | Saisonnalité mensuelle (CROSS actifs) | `annee, mois` |
| `v_kpi_phase_journee_cross_actifs_mv` | Phase journée (CROSS actifs) | `annee, phase_journee` |
| `v_kpi_impact_vacances_cross_actifs_mv` | Vacances scolaires (CROSS actifs) | `annee, en_vacances` |
| `v_kpi_meteo_correlation_cross_actifs_mv` | Corrélations météo (CROSS actifs) | `annee, vent_force, mer_force` |

### Stratégie de Cache

```
┌─────────────────────────────────────────────────────────┐
│           NIVEAU 1 : Vues Matérialisées                 │
│                                                         │
│   PostgreSQL stocke les résultats sur disque            │
│   Refresh après chaque ETL                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           NIVEAU 2 : Cache Streamlit                    │
│                                                         │
│   @st.cache_data(ttl=3600)                              │
│   @st.cache_resource(ttl=3600)                          │
│   Données en mémoire pendant 1 heure                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           NIVEAU 3 : Filtrage In-Memory                 │
│                                                         │
│   Pandas DataFrame filtré instantanément                │
│   Aucune requête SQL pour les changements de filtres    │
└─────────────────────────────────────────────────────────┘
```

### Refresh des Vues

Fichier : `src/database/connection.py`

```python
def refresh_materialized_views() -> bool:
    """Rafraîchir toutes les vues matérialisées après ETL."""
    session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY operations_stats"))
    session.execute(text("REFRESH MATERIALIZED VIEW v_kpi_global"))
    session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_annuel"))
    # ... autres vues
```

---

## Fichiers Modifiés

| Fichier | Modifications |
|---------|---------------|
| `sql/clean_tables.sql` | + vues matérialisées (CROSS actifs inclus) |
| `sql/refresh_materialized_views.sql` | Script de refresh (vues CROSS actifs incluses) |
| `src/database/base_queries.py` | Requêtes optimisées + cache_resource |
| `src/database/kpi_queries.py` | Utilisation des vues matérialisées |
| `src/database/connection.py` | Fonction `refresh_materialized_views()` |
| `src/utils/dataframe_filters.py` | Filtrage in-memory Pandas |
| `src/utils/performance.py` | Outil de diagnostic |
| `src/utils/warmload.py` | Pré-chargement des caches au démarrage |
| `app/main.py` | Import des fonctions optimisées + warmload |
| `app/pages/1_Dashboard.py` | Chargement depuis 2020 par défaut |

---

## Commandes de Vérification

```bash
# Lancer le diagnostic de performance
uv run streamlit run app/pages/11_Diagnostic.py

# Appliquer les vues matérialisées (après modifications SQL)
uv run python -c "from src.etl.pipelines import pipeline_db_cleaned; pipeline_db_cleaned()"

# Vérifier les vues créées
psql $DATABASE_URL -c "SELECT matviewname FROM pg_matviews WHERE schemaname = 'clean';"
```

---

## Conclusion

L'optimisation des performances a permis de réduire le temps de chargement de **43 secondes à environ 4-6 secondes** (86-90% de gain), principalement grâce à :

1. **Vues matérialisées** : Pré-calcul des agrégats coûteux (9 vues)
2. **Cache multi-niveaux** : PostgreSQL + Streamlit + In-memory
3. **Filtrage in-memory** : Évite les requêtes SQL pour chaque changement de filtre
4. **Limitation temporelle** : Chargement depuis 2020 par défaut (dashboard), paramétrable
5. **Warmload** : Pré-chargement des caches critiques au démarrage

Ces optimisations respectent les bonnes pratiques PostgreSQL et sont adaptées au contexte d'une base hébergée sur Render.com avec une latence réseau significative (~87-115ms).

---

## Phase 5 : Optimisations Supplémentaires

### 5.1 Nouvelles vues matérialisées

#### `v_kpi_alertes_anomalies_mv`
Pré-calcule les z-scores et alertes mensuels avec moyennes mobiles sur 12 mois :
- Évite les CTE complexes avec fenêtres glissantes
- **Gain** : 2-5s → 10ms (99% plus rapide)

#### `v_kpi_securite_mensuel_mv`
Pré-calcule les KPIs de sécurité mensuels :
- Taux de saines/sauves, mortalité, disparition, blessures
- Indice de gravité composite
- **Gain** : 500ms → 10ms (98% plus rapide)

### 5.2 Warmload au démarrage

Module : `src/utils/warmload.py`

```python
def warmload_critical_caches():
    """Pré-charge les caches critiques au démarrage."""
    get_kpis_global()          # 10ms
    get_yearly_stats_cached()  # 10ms
    get_cross_stats_cached()   # 10ms
```

Intégré dans `app/main.py` après l'authentification pour réduire le temps de premier chargement des pages.

### 5.3 Correction de bugs

- **Bug `_mv_mv`** : Corrigé dans `kpi_queries.py` (lignes 321, 329)
- **Colonne manquante** : Ajout de `distance_cote_moyenne_m` dans `v_kpi_flotteurs_categorie_mv`
- **Durée moyenne** : Ignore les durées négatives (fin < début) dans `v_kpi_global`

### 5.4 Optimisation du toggle CROSS actifs

Quand `cross_actifs_seulement=True`, des requêtes lourdes recalculaient les agrégats.
Des vues matérialisées dédiées ont été ajoutées pour les pages KPI afin de rendre le toggle instantané.
