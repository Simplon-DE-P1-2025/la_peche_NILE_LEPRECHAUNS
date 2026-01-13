"""Validations cross-field personnalisees.

Regles metier impliquant plusieurs champs.

Usage:
    from src.validation.validators import coordinates_check, coordinates_in_france

    schema = DataFrameSchema(
        columns={...},
        checks=[coordinates_check(), coordinates_in_france()],
    )
"""

import pandas as pd
from pandera import Check


def coordinates_check() -> Check:
    """Latitude et longitude doivent etre fournies ensemble.

    Returns:
        Check Pandera pour validation cross-field
    """

    def check_fn(df: pd.DataFrame) -> bool:
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return True
        lat_null = df["latitude"].isna()
        lon_null = df["longitude"].isna()
        return (lat_null == lon_null).all()

    return Check(
        check_fn,
        name="coordinates_consistency",
        error="Latitude et longitude doivent etre fournies ensemble ou toutes deux absentes",
    )


def coordinates_in_france() -> Check:
    """Verifier que les coordonnees sont dans la zone France.

    Inclut metropole et DOM-TOM. Retourne un warning (pas d'erreur bloquante).

    Returns:
        Check Pandera pour validation geographique
    """

    def check_fn(df: pd.DataFrame) -> pd.Series:
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return pd.Series([True] * len(df), index=df.index)

        lat = df["latitude"]
        lon = df["longitude"]

        # Si null, valide
        null_mask = lat.isna() | lon.isna()

        # France metropolitaine (lat 41-51, lon -5 a 10)
        metro = (lat >= 41) & (lat <= 51) & (lon >= -5) & (lon <= 10)

        # Antilles (~14-18N, -64 to -60W)
        antilles = (lat >= 14) & (lat <= 18) & (lon >= -64) & (lon <= -60)

        # Reunion (~-21S, 55E)
        reunion = (lat >= -22) & (lat <= -20) & (lon >= 54) & (lon <= 56)

        # Polynesie (~-20S, -150W)
        polynesie = (lat >= -25) & (lat <= -10) & (lon >= -155) & (lon <= -130)

        # Nouvelle-Caledonie (~-22S, 165E)
        nouvelle_caledonie = (lat >= -23) & (lat <= -19) & (lon >= 163) & (lon <= 169)

        # Mayotte (~-13S, 45E)
        mayotte = (lat >= -14) & (lat <= -12) & (lon >= 44) & (lon <= 46)

        # Guyane (~4N, -53W)
        guyane = (lat >= 2) & (lat <= 6) & (lon >= -55) & (lon <= -51)

        return (
            null_mask
            | metro
            | antilles
            | reunion
            | polynesie
            | nouvelle_caledonie
            | mayotte
            | guyane
        )

    return Check(
        check_fn,
        element_wise=False,
        name="coordinates_in_france",
        error="Coordonnees hors zone France (verification informative)",
        raise_warning=True,  # Warning au lieu d'erreur
    )


def resultat_humain_coherence() -> Check:
    """Le nombre de personnes doit etre positif si un resultat est specifie.

    Returns:
        Check Pandera pour validation coherence resultat/nombre
    """

    def check_fn(df: pd.DataFrame) -> bool:
        if "resultat_humain" not in df.columns or "nombre" not in df.columns:
            return True

        has_resultat = df["resultat_humain"].notna() & (df["resultat_humain"] != "")
        has_nombre = df["nombre"] >= 1

        # Si resultat specifie, nombre doit etre >= 1
        return (~has_resultat | has_nombre).all()

    return Check(
        check_fn,
        name="resultat_nombre_coherence",
        error="Un resultat humain doit avoir un nombre de personnes >= 1",
    )


def flotteur_longueur_type_coherence() -> Check:
    """Verification coherence longueur/type flotteur.

    Ex: Un kayak ne fait pas 50m.

    Returns:
        Check Pandera pour validation coherence type/longueur
    """
    type_max_lengths = {
        "Canoe/Kayak": 6.0,
        "Jet-ski": 5.0,
        "Planche a voile": 5.0,
        "Kitesurf": 3.0,
        "Engin de plage": 4.0,
        "Ski nautique": 3.0,
    }

    def check_fn(df: pd.DataFrame) -> pd.Series:
        if "type_flotteur" not in df.columns or "longueur" not in df.columns:
            return pd.Series([True] * len(df), index=df.index)

        results = pd.Series([True] * len(df), index=df.index)

        for type_flotteur, max_len in type_max_lengths.items():
            mask = df["type_flotteur"] == type_flotteur
            if mask.any():
                longueur_ok = df.loc[mask, "longueur"].isna() | (
                    df.loc[mask, "longueur"] <= max_len
                )
                results.loc[mask] = longueur_ok

        return results

    return Check(
        check_fn,
        element_wise=False,
        name="flotteur_longueur_coherence",
        error="Longueur incoherente avec le type de flotteur",
    )


def beaufort_scale_check() -> Check:
    """Valide l'echelle de Beaufort (0-12).

    Returns:
        Check Pandera pour vent_force
    """

    def check_fn(value: int) -> bool:
        if value is None:
            return True
        return 0 <= int(value) <= 12

    return Check(check_fn, element_wise=True, name="beaufort_scale", error="Force du vent doit etre entre 0 et 12 (echelle Beaufort)")


def douglas_scale_check() -> Check:
    """Valide l'echelle de Douglas (0-9).

    Returns:
        Check Pandera pour mer_force
    """

    def check_fn(value: int) -> bool:
        if value is None:
            return True
        return 0 <= int(value) <= 9

    return Check(check_fn, element_wise=True, name="douglas_scale", error="Force de la mer doit etre entre 0 et 9 (echelle Douglas)")


def departement_format_check() -> Check:
    """Valide le format du departement (2-3 caracteres).

    Returns:
        Check Pandera pour departement
    """

    def check_fn(value: str) -> bool:
        if value is None or value == "":
            return True
        # Format: 01-95, 2A, 2B, 971-976
        return len(str(value)) <= 3

    return Check(
        check_fn, element_wise=True, name="departement_format", error="Format departement invalide (2-3 caracteres max)"
    )
