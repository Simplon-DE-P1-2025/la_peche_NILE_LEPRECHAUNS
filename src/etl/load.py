import pandas as pd
from sqlalchemy.engine import Engine

def load_df_to_db(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "replace",
    schema: str | None = None,
) -> None:
    """
    Charge un DataFrame dans PostgreSQL avec gestion d'erreur propre.
    La transaction est automatiquement commit/rollback.
    """

    try:
        with engine.begin() as conn:
            df.to_sql(
                name=table_name,
                con=conn,
                schema=schema,
                if_exists=if_exists,
                index=False,
                method="multi",
            )

        print(f"✅ Données chargées dans la table {table_name}")

    except Exception as e:
        print(f"❌ Erreur lors du chargement de la table {table_name}")
        print(f"   Détails : {e}")
        raise