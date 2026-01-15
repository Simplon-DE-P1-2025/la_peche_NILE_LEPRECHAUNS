# sql/ - Scripts SQL

> Scripts SQL pour la creation des tables et vues KPI.

## But

Ce dossier contient les scripts SQL pour initialiser la base de donnees et creer les vues necessaires aux KPIs.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `stub_tables.sql` | Creation des tables et donnees de test |
| `views_kpi.sql` | Vues SQL pour les indicateurs de performance |

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

## Utilisation

```bash
# Initialiser la base de donnees
psql -U postgres -d secmar -f sql/stub_tables.sql

# Creer les vues KPI
psql -U postgres -d secmar -f sql/views_kpi.sql
```

## Lien avec src/database/

Les scripts SQL correspondent aux modeles ORM definis dans `src/database/models.py`. Toute modification de schema doit etre synchronisee entre les deux.
