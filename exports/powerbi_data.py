"""Script d'export des données pour Power BI.

Ce script exporte les vues KPI en fichiers CSV/Parquet pour import dans Power BI.

Usage:
    python exports/powerbi_data.py --format csv --output ./powerbi_exports
    python exports/powerbi_data.py --format parquet --output ./powerbi_exports
    python exports/powerbi_data.py --views v_kpi_securite_mensuel v_kpi_cross_benchmark

Date: Janvier 2026
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.database.kpi_queries import export_kpi_to_dataframe

# Liste des vues KPI disponibles
AVAILABLE_VIEWS = [
    "v_kpi_securite_mensuel",
    "v_kpi_cross_benchmark",
    "v_kpi_flotteurs_analyse",
    "v_kpi_temporel_multidim",
    "v_kpi_meteo_correlation",
    "v_kpi_yoy_comparison",
    "v_kpi_alertes_anomalies",
    "v_kpi_geographique",
    "v_kpi_type_operation",
]


def export_view(view_name: str, output_dir: str, file_format: str = "csv") -> str:
    """Exporter une vue KPI en fichier.

    Args:
        view_name: Nom de la vue SQL
        output_dir: Dossier de sortie
        file_format: Format de sortie ('csv' ou 'parquet')

    Returns:
        Chemin du fichier exporté
    """
    print(f"  Exporting {view_name}...", end=" ")

    try:
        df = export_kpi_to_dataframe(view_name)

        if df.empty:
            print("SKIP (empty)")
            return None

        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{view_name}_{timestamp}"

        if file_format == "csv":
            filepath = os.path.join(output_dir, f"{filename}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8")
        elif file_format == "parquet":
            filepath = os.path.join(output_dir, f"{filename}.parquet")
            df.to_parquet(filepath, index=False)
        else:
            raise ValueError(f"Format non supporté: {file_format}")

        print(f"OK ({len(df)} rows) -> {filepath}")
        return filepath

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def export_all_views(
    output_dir: str, file_format: str = "csv", views: list = None
) -> dict:
    """Exporter toutes les vues KPI.

    Args:
        output_dir: Dossier de sortie
        file_format: Format de sortie
        views: Liste des vues à exporter (optionnel, toutes par défaut)

    Returns:
        Dictionnaire {view_name: filepath}
    """
    # Créer le dossier de sortie si nécessaire
    os.makedirs(output_dir, exist_ok=True)

    views_to_export = views or AVAILABLE_VIEWS
    results = {}

    print(f"\n{'='*60}")
    print(f"Export Power BI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Output: {output_dir}")
    print(f"Format: {file_format}")
    print(f"Views: {len(views_to_export)}")
    print(f"{'='*60}\n")

    for view in views_to_export:
        filepath = export_view(view, output_dir, file_format)
        results[view] = filepath

    # Résumé
    success = sum(1 for v in results.values() if v is not None)
    print(f"\n{'='*60}")
    print(f"Export terminé: {success}/{len(views_to_export)} vues exportées")
    print(f"{'='*60}\n")

    return results


def create_powerbi_manifest(output_dir: str, exported_files: dict) -> str:
    """Créer un fichier manifest pour Power BI.

    Args:
        output_dir: Dossier de sortie
        exported_files: Dictionnaire des fichiers exportés

    Returns:
        Chemin du fichier manifest
    """
    manifest = {
        "export_date": datetime.now().isoformat(),
        "files": [
            {"view": view, "path": path, "description": get_view_description(view)}
            for view, path in exported_files.items()
            if path is not None
        ],
    }

    # Export en JSON
    import json

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest créé: {manifest_path}")
    return manifest_path


def get_view_description(view_name: str) -> str:
    """Obtenir la description d'une vue KPI.

    Args:
        view_name: Nom de la vue

    Returns:
        Description de la vue
    """
    descriptions = {
        "v_kpi_securite_mensuel": "Indicateurs de sécurité mensuels (taux sauvetage, mortalité, gravité)",
        "v_kpi_cross_benchmark": "Performance et ranking des CROSS (durées, taux, classement)",
        "v_kpi_flotteurs_analyse": "Statistiques par type et catégorie de flotteur",
        "v_kpi_temporel_multidim": "Analyse temporelle multi-dimensions (phase jour, vacances, météo)",
        "v_kpi_meteo_correlation": "Corrélations météo / gravité des incidents",
        "v_kpi_yoy_comparison": "Comparatifs année sur année (YoY)",
        "v_kpi_alertes_anomalies": "Détection d'anomalies statistiques (z-scores)",
        "v_kpi_geographique": "Analyse géographique par zone et département",
        "v_kpi_type_operation": "Statistiques par type d'opération (SAR, MAS, etc.)",
    }
    return descriptions.get(view_name, "Vue KPI SECMAR")


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Export des données KPI SECMAR pour Power BI"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "parquet"],
        default="csv",
        help="Format de sortie (défaut: csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./powerbi_exports",
        help="Dossier de sortie (défaut: ./powerbi_exports)",
    )
    parser.add_argument(
        "--views",
        "-v",
        nargs="+",
        choices=AVAILABLE_VIEWS,
        help="Vues spécifiques à exporter (défaut: toutes)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Lister les vues disponibles et quitter",
    )

    args = parser.parse_args()

    # Mode liste
    if args.list:
        print("\nVues KPI disponibles:")
        print("-" * 60)
        for view in AVAILABLE_VIEWS:
            print(f"  - {view}")
            print(f"    {get_view_description(view)}")
        print()
        return

    # Export
    results = export_all_views(args.output, args.format, args.views)

    # Création du manifest
    create_powerbi_manifest(args.output, results)


if __name__ == "__main__":
    main()
