# sql/ - Scripts SQL

> Scripts SQL pour la creation des tables et vues KPI.

## But

Ce dossier contient les scripts SQL pour initialiser la base de donnees et creer les vues necessaires aux KPIs.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `stub_tables.sql` | Creation des tables et donnees de test |
| `clean_tables.sql` | Creation des tables alignees sur le MCD SECMAR |
| `views_kpi.sql` | Vues SQL pour les indicateurs de performance |
| `check_indexes.sql` | Diagnostic des index et performances |
| `optimize_performance.sql` | Creation des index et vues materialisees |
| `refresh_materialized_views.sql` | Rafraichissement des vues materialisees apres ETL |

## stub_tables.sql

Script de creation des tables principales :
- `operations` : Operations de sauvetage maritime
- `flotteurs` : Flotteurs impliques
- `resultats_humain` : Personnes secourues/impliquees
- `users` : Utilisateurs de l'application
- `audit_log` : Journal des modifications

Inclut des donnees de test pour le developpement.

## views_kpi.sql

Vues SQL precalculees pour les KPIs :
- Agregations par CROSS
- Agregations par type d'operation
- Statistiques temporelles
- Indicateurs de performance

## check_indexes.sql

Script de diagnostic pour verifier l'etat des index et performances :
- Liste des index existants
- Comptage des lignes par table
- Analyse de la taille des tables

## optimize_performance.sql

Script d'optimisation des performances :
- Creation des index manquants (date, CROSS, type)
- Conversion des vues en vues materialisees
- Index composites pour les requetes courantes

## refresh_materialized_views.sql

Script de rafraichissement des vues materialisees :
- A executer apres chaque chargement ETL
- Rafraichit toutes les vues KPI de maniere concurrente

## Utilisation

```bash
# Initialiser la base de donnees
psql -U postgres -d secmar -f sql/stub_tables.sql

# Creer les vues KPI
psql -U postgres -d secmar -f sql/views_kpi.sql

# Optimiser les performances (production)
psql $DATABASE_URL -f sql/optimize_performance.sql

# Rafraichir les vues materialisees (apres ETL)
psql $DATABASE_URL -f sql/refresh_materialized_views.sql

# Diagnostiquer les performances
psql $DATABASE_URL -f sql/check_indexes.sql
```

## Lien avec src/database/

Les scripts SQL correspondent aux modeles ORM definis dans `src/database/models.py`. Toute modification de schema doit etre synchronisee entre les deux.
