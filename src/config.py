"""Configuration centralisée - STUB pour CRUD.

TODO: L'équipier doit compléter ce fichier avec :
- Chemins DATA_DIR, RAW_DIR, PROCESSED_DIR
- URLs SECMAR_URLS
- Paramètres de pool DB_POOL_SIZE, DB_MAX_OVERFLOW
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Chemins
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

# Créer les répertoires si nécessaire
for dir_path in [RAW_DIR, PROCESSED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Base de données
# =============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://secmar:secmar@localhost:5432/secmar_db"
)
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

# =============================================================================
# URLs SECMAR (TODO: Sprint 1 doit compléter)
# =============================================================================
SECMAR_URLS = {
    "operations": "https://www.data.gouv.fr/fr/datasets/r/...",
    "flotteurs": "https://www.data.gouv.fr/fr/datasets/r/...",
    "resultats_humain": "https://www.data.gouv.fr/fr/datasets/r/...",
    "operations_stats": "https://www.data.gouv.fr/fr/datasets/r/...",
}

# =============================================================================
# Application
# =============================================================================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
