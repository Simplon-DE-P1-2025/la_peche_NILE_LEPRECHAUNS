from etl.extract import load_config, extract_url
from validation.schema_validation import build_dataframe_schema, valider_csv
from pathlib import Path
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

        valider_csv(
            csv_path=csv_path,
            schema=schema,
            lazy=True
        )



if __name__ == "__main__":
    main()