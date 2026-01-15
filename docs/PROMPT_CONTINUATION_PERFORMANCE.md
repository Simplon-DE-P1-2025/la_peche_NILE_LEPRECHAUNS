# Prompt pour Continuer l'Optimisation Performance SECMAR

## Contexte Projet

Tu travailles sur **SECMAR Dashboard**, une application Streamlit connectée à PostgreSQL sur Render.com. La base contient **385 782 opérations** de sauvetage maritime.

**Problème initial** : Temps de chargement ~43 secondes à cause de la latence réseau (~90ms) et des requêtes SQL complexes.

---

## Ce qui a été fait (Phases 1-3) ✅

### Phase 1 : Vue `operations_stats`
- Vue matérialisée pré-calculant les métriques SECMAR par opération
- **Gain** : 88s → 43s (51%)

### Phase 2 : Vues KPI + Filtrage In-Memory
- `v_kpi_global` : KPIs globaux
- `v_kpi_annuel` : Stats par année
- `v_kpi_cross` : Stats par CROSS
- `src/utils/dataframe_filters.py` : Filtrage Pandas en mémoire
- **Gain** : `get_kpis` 12.6s → 10ms (99%)

### Phase 3 : YoY et Données de Base
- `v_kpi_yoy_cross_actifs` : Comparatifs Year-over-Year
- `get_operations_base(years_back=3)` : Limitation temporelle
- **Gain** : `get_kpi_yoy_latest` 6.9s → 109ms (98%)

### Résultats actuels
- **Total sans cache** : 5877ms (vs 27624ms initial)
- **Total avec cache** : 128ms
- **Efficacité cache** : 97.8%

---

## Phase 4 : CE QUI RESTE À CORRIGER ❌

### Bug 1 : Double suffix `_mv_mv`
**Fichier** : `src/database/kpi_queries.py` (lignes 321, 329)
```python
# ERREUR - double _mv
FROM v_kpi_cross_benchmark_mv_mv  # ❌

# CORRECTION
FROM v_kpi_cross_benchmark_mv     # ✅
```

### Bug 2 : Colonne manquante `distance_cote_moyenne_m`
**Fichier** : `sql/clean_tables.sql` - vue `v_kpi_flotteurs_categorie_mv`

La page `8_Analyse_Flotteurs.py` (ligne 132) attend la colonne `distance_cote_moyenne_m` mais la vue matérialisée ne l'inclut pas.

**Solution** : Ajouter cette colonne à la vue matérialisée :
```sql
-- Ajouter dans la SELECT de v_kpi_flotteurs_categorie_mv :
ROUND(AVG(f.distance_cote_metres)::NUMERIC, 0) as distance_cote_moyenne_m
```

### Pages encore lentes à optimiser
| Page | Problème |
|------|----------|
| KPI Sécurité | `get_kpi_securite_global` ~528ms |
| Saisonnalité & Météo | Temps moyen |
| Alertes & Anomalies | Long |

---

## Fichiers clés

```
sql/clean_tables.sql           # Définition des vues matérialisées
src/database/kpi_queries.py    # Fonctions KPI (bug _mv_mv ici)
src/database/connection.py     # refresh_materialized_views()
sql/refresh_materialized_views.sql
app/pages/7_Performance_CROSS.py
app/pages/8_Analyse_Flotteurs.py
src/utils/performance.py       # Outil diagnostic
docs/PERFORMANCE_OPTIMIZATION.md
```

---

## Actions à faire

1. **Corriger le bug `_mv_mv`** dans `kpi_queries.py` (lignes 321, 329)
   - Remplacer `v_kpi_cross_benchmark_mv_mv` par `v_kpi_cross_benchmark_mv`

2. **Ajouter la colonne manquante** dans `sql/clean_tables.sql`
   - Ajouter `distance_cote_moyenne_m` à `v_kpi_flotteurs_categorie_mv`

3. **Relancer l'ETL** pour appliquer les changements :
   ```bash
   uv run python -c "from src.etl.pipelines import pipeline_db_cleaned; pipeline_db_cleaned()"
   ```

4. **Vérifier avec le diagnostic** :
   ```bash
   uv run streamlit run app/pages/11_Diagnostic.py
   ```

5. **Optionnel** : Optimiser les pages encore lentes (KPI Sécurité, Alertes)

---

## Commandes utiles

```bash
# Diagnostic performance
uv run streamlit run app/pages/11_Diagnostic.py

# Lancer le dashboard
uv run streamlit run app/main.py

# Appliquer les vues SQL
uv run python -c "from src.etl.pipelines import pipeline_db_cleaned; pipeline_db_cleaned()"

# Vérifier les vues PostgreSQL
psql $DATABASE_URL -c "SELECT matviewname FROM pg_matviews WHERE schemaname = 'clean';"
```

---

## Documentation existante

Le fichier `docs/PERFORMANCE_OPTIMIZATION.md` contient la documentation complète de toutes les optimisations pour présentation aux examinateurs.
