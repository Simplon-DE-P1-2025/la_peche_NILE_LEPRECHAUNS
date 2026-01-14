import os
from pathlib import Path
from dotenv import load_dotenv

from etl.extract import load_config, extract_url
from etl.load import load_df_to_db
from validation.schema_validation import build_dataframe_schema, valider_csv
from database.connection import create_postgres_engine, execute_sql_file

import time
import pandas as pd
from functools import wraps


load_dotenv()

def pipeline_db_raw() -> None:
    """
    Pipeline ETL pour l'alimentation de la base de données RAW.

    Étapes du pipeline :
    1. Chargement de la configuration depuis le fichier YAML.
    2. Extraction des fichiers CSV depuis les URLs configurées.
    3. Construction dynamique des schémas de validation Pandera
       à partir de la section DATA_VALIDATION du fichier de configuration.
    4. Validation des fichiers CSV (mode lazy) et récupération
       des données valides uniquement.
    5. Chargement des données validées dans la base PostgreSQL
       dans le schéma RAW.

    Ce pipeline ne génère pas de rapport métier et s'arrête en cas
    d'erreur critique lors du chargement en base.

    Returns
    -------
    None
    """
    cfg = load_config("config/config.yml")

    # Étape 1 — Extraction des fichiers CSV
    _data_list = extract_url(
        dataset_url=cfg['EXTRACT']['dataset_url'],
        timeout_sec=cfg['EXTRACT']['timeout_sec'],
        output_dir=cfg['EXTRACT']['output_dir']
    )

    # Étape 2 — Construction des schémas de validation Pandera
    data_validation = cfg['DATA_VALIDATION']
    pandera_schemas = {}

    for schema_name, schema_def in data_validation.items():
        pandera_schemas[schema_name] = build_dataframe_schema(schema_def)

    # Étape 3 — Validation et chargement en base
    for schema_name, schema in pandera_schemas.items():
        csv_path = Path(f"{cfg['EXTRACT']['output_dir']}/{schema_name}.csv")

        # Validation des données (lazy pour récupérer toutes les erreurs)
        df = valider_csv(
            csv_path=csv_path,
            schema=schema,
            lazy=True
        )

        # Création de l'engine PostgreSQL
        engine = create_postgres_engine(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_DATABASE"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

        # Chargement des données validées dans le schéma RAW
        load_df_to_db(
            df=df,
            table_name=schema_name,
            engine=engine,
            if_exists="replace",
            schema="raw_test"  # à supprimer si non nécessaire
        )

def pipeline_db_cleaned() -> None:
    """
    Pipeline ETL pour l'alimentation de la base de données CLEANED.

    À implémenter.

    Returns
    -------
    None
    """

    cfg = load_config("config/config_clean.yml")

    # Étape 1 — Extraction des fichiers CSV
    _data_list = extract_url(
        dataset_url=cfg['EXTRACT']['dataset_url'],
        timeout_sec=cfg['EXTRACT']['timeout_sec'],
        output_dir=cfg['EXTRACT']['output_dir']
    )

    # Étape 2 — Construction des schémas de validation Pandera
    data_validation = cfg['DATA_VALIDATION']
    pandera_schemas = {}

    for schema_name, schema_def in data_validation.items():
        pandera_schemas[schema_name] = build_dataframe_schema(
            schema_def, 
            strict_method=True
            )
    
    # Étape 3 — Validation et chargement en base

    dfs_validated = {}

    for schema_name, schema in pandera_schemas.items():
        csv_path = Path(f"{cfg['EXTRACT']['output_dir']}/{schema_name}.csv")

        # Validation des données (lazy pour récupérer toutes les erreurs)
        df = valider_csv(
            csv_path=csv_path,
            schema=schema,
            lazy=True
        )
        df_filtered = df.loc[:, schema.columns.keys()]
        dfs_validated[schema_name] = df_filtered

    df_operations = pd.merge(
        dfs_validated["operations"],
        dfs_validated["operations_stats"],
        on="operation_id",
        how="left"
    )
    
    print(dfs_validated.keys())
    
    # engine = create_postgres_engine(
    #     host=os.getenv("DB_HOST"),
    #     database=os.getenv("DB_DATABASE"),
    #     user=os.getenv("DB_USER"),
    #     password=os.getenv("DB_PASSWORD")
    # )

    # execute_sql_file("sql/clean_tables.sql", engine)

    # #Chargement des données validées dans le schéma CLEANED
    # for schema_name, df in dfs_validated.items():
    #     load_df_to_db(
    #         df=df,
    #         table_name=schema_name,
    #         engine=engine,
    #         if_exists="append",
    #         schema="clean"  # à supprimer si non nécessaire
    # )

    pass
