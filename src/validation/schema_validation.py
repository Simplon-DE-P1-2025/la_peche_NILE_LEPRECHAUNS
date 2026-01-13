import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from pandera.errors import SchemaErrors
from pathlib import Path
import datetime

TYPE_MAPPING = {
    "int": pa.Int,
    "str": pa.String,
    "float": pa.Float,
    "float64": pa.Float,
    "bool": pa.Bool,
    "datetime": pa.DateTime
}

def build_dataframe_schema(schema_dict: dict) -> DataFrameSchema:
    columns = {}

    for col_name, col_props in schema_dict.items():
        col_type = TYPE_MAPPING[col_props["type"]]
        nullable = col_props.get("nullable", True)
        unique = col_props.get("unique", False)

        checks = []

        # Format moderne : checks:
        for check in col_props.get("checks", []):
            if "greater_than" in check:
                checks.append(Check.greater_than(check["greater_than"]))
            elif "less_than" in check:
                checks.append(Check.less_than(check["less_than"]))
            elif "isin" in check:
                checks.append(Check.isin(check["isin"]))

        # Format simple : check: "x >= 0"
        if "check" in col_props:
            expr = col_props["check"]
            checks.append(Check(lambda x, e=expr: eval(e, {"x": x})))

        columns[col_name] = Column(
            col_type,
            checks=checks if checks else None,
            nullable=nullable,
            unique=unique
        )

    return DataFrameSchema(columns)

def valider_csv(csv_path, schema, lazy=True):
    df = pd.read_csv(csv_path, low_memory=False)
    csv_path = Path(csv_path)
    base_name = csv_path.stem

    valid_dir = Path("data/raw_valid")
    rejected_dir = Path("data/raw_rejected")
    errors_dir = Path("data/raw_errors")

    valid_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    errors_dir.mkdir(parents=True, exist_ok=True)

    valid_file = valid_dir / f"{base_name}_valid.csv"
    rejected_file = rejected_dir / f"{base_name}_rejected.csv"
    errors_file = errors_dir / f"{base_name}_errors.csv"

    try:
        schema.validate(df, lazy=lazy)
        df.to_csv(valid_file, index=False)

        return print({
            "file": csv_path.name,
            "nb_erreurs": 0,
            "nb_lignes_valides": len(df),
            "nb_lignes_rejetees": 0,
        })

    except SchemaErrors as e:
        errors_df = e.failure_cases

        error_indexes = (
            errors_df["index"]
            .dropna()
            .astype(int)
            .unique()
        )

        rejected_df = df.loc[error_indexes]
        valid_df = df.drop(error_indexes)

        valid_df.to_csv(valid_file, index=False)
        rejected_df.to_csv(rejected_file, index=False)
        errors_df.to_csv(errors_file, index=False)

        return print({
            "file": csv_path.name,
            "nb_erreurs": len(errors_df),                     # violations
            "nb_lignes_rejetees": errors_df["index"].nunique(), # lignes impactées
            "nb_lignes_valides": len(valid_df)
        })
        
    
