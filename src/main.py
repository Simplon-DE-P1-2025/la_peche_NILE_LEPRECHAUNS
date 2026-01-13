from etl.extract import load_config, extract_url
from validation.schema_validation import build_dataframe_schema, valider_csv
from pathlib import Path
from database.connection import create_postgres_engine
from dotenv import load_dotenv
import os

load_dotenv()


def main() -> None:

    cfg = load_config("config/config.yml")
    


    _data_list = extract_url(
        dataset_url=cfg['EXTRACT']['dataset_url'],
        timeout_sec=cfg['EXTRACT']['timeout_sec'],
        output_dir=cfg['EXTRACT']['output_dir']
        )
    
    data_validation = cfg['DATA_VALIDATION']
    
    pandera_schemas = {}

    for schema_name, schema_def in data_validation.items():
        pandera_schemas[schema_name] = build_dataframe_schema(schema_def)
    
    for schema_name, schema in pandera_schemas.items():
        csv_path = Path(f"{cfg['EXTRACT']['output_dir']}/{schema_name}.csv")

        df = valider_csv(
            csv_path=csv_path,
            schema=schema,
            lazy=True
        )
        engine = create_postgres_engine(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        with engine.begin() as conn:  # begin() gère transaction automatiquement
            try:
                df.to_sql(
                    name=schema_name,
                    con=conn,          # <- utiliser la connexion transactionnelle
                    if_exists="replace",
                    index=False,
                    # method="multi"
                )
                print(f"Données chargées avec succès dans la table {schema_name}")

            except Exception as e:
                print(f"Erreur lors du chargement dans la table {schema_name}: {e}")
                raise
            finally:
                # engine.dispose() ferme le pool proprement
                engine.dispose()
                print(f"Connexion fermée pour {schema_name}")
 

if __name__ == "__main__":
    main()