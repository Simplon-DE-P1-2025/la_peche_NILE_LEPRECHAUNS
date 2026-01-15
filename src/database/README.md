# src/database/ - Couche de Donnees

> Interface d'acces a la base de donnees PostgreSQL avec SQLAlchemy.

## But

Ce module gere toutes les interactions avec la base de donnees : connexion, modeles ORM, operations CRUD et audit des modifications.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `connection.py` | Connexion PostgreSQL, sessionmaker, Base SQLAlchemy |
| `models.py` | Definition des tables ORM (Operation, Flotteur, ResultatHumain, User, AuditLog) |
| `crud.py` | Operations CRUD generiques et specifiques |
| `audit.py` | Systeme d'audit des modifications |
| `enums.py` | Enumerations des domaines metier (types d'operations, CROSS, etc.) |
| `raw_queries.py` | Requetes SQL brutes pour cas specifiques |
| `kpi_queries.py` | Requetes pour les indicateurs de performance |

## Modeles principaux

| Modele | Description |
|--------|-------------|
| `Operation` | Operation de sauvetage maritime SECMAR |
| `Flotteur` | Navire/flotteur implique dans une operation |
| `ResultatHumain` | Personne secourue ou impliquee |
| `User` | Utilisateur de l'application |
| `AuditLog` | Journal des modifications |

## Utilisation

```python
from src.database.connection import get_session
from src.database.crud import crud_operation

# Lire une operation
with get_session() as session:
    op = crud_operation.get(session, operation_id=123)

# Creer une operation
with get_session() as session:
    new_op = crud_operation.create(session, data={...})
```

## Dependances

- SQLAlchemy 2.0+
- psycopg2 (driver PostgreSQL)
- python-dotenv (variables d'environnement)
