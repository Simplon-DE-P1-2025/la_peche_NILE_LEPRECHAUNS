from pathlib import Path
import requests
import yaml
from typing import List

def load_config(config_path: str = "config.yml") -> dict:
    """
    Charge la configuration depuis un fichier YAML.

    :param config_path: chemin vers le fichier config.yml
    :return: dictionnaire de configuration
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_url(dataset_url: str, timeout_sec: int = 20, output_dir: str = ".") -> List[Path]:
    """
    Télécharge automatiquement tous les fichiers CSV d'un dataset data.gouv.fr
    et retourne la liste des fichiers téléchargés.

    :param dataset_url: URL du dataset sur data.gouv.fr
    :param timeout_sec: Timeout en secondes pour les requêtes HTTP
    :param output_dir: Répertoire de sortie pour les fichiers CSV
    :return: Liste des chemins complets des fichiers CSV téléchargés
    """
    downloaded_files = []

    # 1. Récupération des métadonnées du dataset
    try:
        resp = requests.get(dataset_url, timeout=(3, timeout_sec))
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout dépassé pour {dataset_url}")
        return downloaded_files
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP pour {dataset_url} : {e}")
        return downloaded_files
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau pour {dataset_url} : {e}")
        return downloaded_files

    # 2. Création du dossier de sortie si nécessaire
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 3. Téléchargement des fichiers CSV
    for resource in data.get("resources", []):
        if resource.get("format", "").lower() == "csv":
            csv_url = resource["url"]
            filename = resource["title"].replace(" ", "_")
            file_path = output_path / filename

            print(f"Téléchargement : {filename} depuis {csv_url}")

            try:
                response = requests.get(csv_url, timeout=(3, timeout_sec))
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)

                # Ajouter le fichier téléchargé à la liste
                downloaded_files.append(file_path)

            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout dépassé pour {csv_url}")
            except requests.exceptions.HTTPError as e:
                print(f"❌ Erreur HTTP pour {csv_url} : {e}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Erreur réseau pour {csv_url} : {e}")
    return downloaded_files

