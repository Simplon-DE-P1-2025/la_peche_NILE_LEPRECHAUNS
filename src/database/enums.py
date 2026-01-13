"""Valeurs officielles SECMAR/SeaMIS - Reference non contraignante.

Ce module centralise les constantes metier utilisees dans l'application.
Les valeurs sont issues des sources officielles SECMAR et du tableur
de transition SeaMIS -> SNOSAN.

Sources:
- https://mtes-mct.github.io/secmar-documentation/tables_codes.html
- Tableur SeaMIS -> SNOSAN transitions

Note importante:
- Ces valeurs servent de REFERENCE, pas de contrainte stricte
- Les donnees historiques (avant 2020) peuvent contenir des valeurs differentes
- La validation Pandera utilise ces listes en mode WARNING (pas erreur)

Usage:
    from src.database.enums import TYPE_OPERATION, CROSS_VALUES

    # Dans un selectbox Streamlit
    st.selectbox("Type", options=TYPE_OPERATION)
"""

# =============================================================================
# Types d'operation
# =============================================================================
# Confirmes dans le tableur de transition SeaMIS
TYPE_OPERATION = [
    "SAR",  # Search And Rescue - Recherche et sauvetage
    "MAS",  # Maritime Assistance Service
    "DIV",  # Divers
    "SUR",  # Surveillance
    "POL",  # Pollution
]


# =============================================================================
# CROSS (Centres Regionaux Operationnels de Surveillance et de Sauvetage)
# =============================================================================
# Inclut les CROSS actifs et historiques pour compatibilite avec donnees anciennes
CROSS_VALUES = [
    # CROSS actifs (metropolitains)
    "Gris-Nez",
    "Jobourg",
    "Corsen",
    "Etel",
    "La Garde",
    "Corse",
    # CROSS actifs (outre-mer)
    "Antilles-Guyane",
    "Nouvelle-Caledonie",
    "Polynesie",
    "Sud ocean Indien",
    # CROSS historiques (fermes mais presents dans donnees anciennes)
    "Adge",
    "La Reunion",
    "Martinique",
    "Mayotte",
    "Soulac",
]


# =============================================================================
# Resultats humains (bilan des personnes)
# =============================================================================
# Valeurs SeaMIS officielles + valeurs legacy SECMAR pour compatibilite
RESULTAT_HUMAIN = [
    # Valeurs SeaMIS (officielles depuis 2020)
    "Personne assistee",
    "Personne decedee",
    "Personne disparue",
    "Personne retrouvee",
    "Personne secourue",
    # Valeurs legacy SECMAR (pour compatibilite donnees anciennes)
    "Sain et sauf",
    "Blesse",
    "Decede",
    "Disparu",
    "Retrouve",
    "Assiste",
    "Inconnu",
]


# =============================================================================
# Categories de personnes
# =============================================================================
CATEGORIE_PERSONNE = [
    "Equipage",
    "Passager",
    "Autre",
    "Inconnu",
]


# =============================================================================
# Resultats flotteurs
# =============================================================================
# 20 valeurs du tableur de transition SeaMIS
RESULTAT_FLOTTEUR = [
    "ASSISTE",
    "AU_MOUILLAGE",
    "A_LA_DERIVE",
    "COULE",
    "DESECHOUE",
    "DETRUIT",
    "DIFFICULTE_SURMONTEE_SEUL",
    "ECHOUE",
    "FAUSSE_ALERTE",
    "IMMOBILISE_DANS_ENGIN",
    "INCONNU",
    "NON_ASSISTE",
    "NON_RETROUVE",
    "PERDU_VOLE",
    "REMORQUE",
    "RENFLOUE",
    "REPRISE_DE_ROUTE",
    "RETROUVE_APRES_RECHERCHE",
    "TIRE_DAFFAIRE_SEUL",
]


# =============================================================================
# Types de flotteurs
# =============================================================================
TYPE_FLOTTEUR = [
    "Aeronef",
    "Canoe/Kayak",
    "Commerce",
    "Navire a passagers",
    "Peche",
    "Plaisance a voile",
    "Plaisance a moteur",
    "Ski nautique",
    "Planche a voile",
    "Kitesurf",
    "Jet-ski",
    "Engin de plage",
    "Annexe",
    "Voilier",
    "Autre",
]


# =============================================================================
# Roles utilisateurs (application Streamlit)
# =============================================================================
ROLE_VALUES = [
    "viewer",   # Lecture seule
    "editor",   # Lecture + ecriture
    "admin",    # Tous les droits
]


# =============================================================================
# Mapping emojis pour affichage UI
# =============================================================================
RESULTAT_EMOJI = {
    # Resultats positifs
    "Sain et sauf": "🟢",
    "Assiste": "🟢",
    "Retrouve": "🟢",
    "Personne assistee": "🟢",
    "Personne retrouvee": "🟢",
    "Personne secourue": "🟢",
    # Resultats negatifs legers
    "Blesse": "🟠",
    # Resultats negatifs graves
    "Decede": "🔴",
    "Personne decedee": "🔴",
    # Disparus
    "Disparu": "⚫",
    "Personne disparue": "⚫",
    # Inconnu
    "Inconnu": "⚪",
}


def get_resultat_emoji(resultat: str) -> str:
    """Retourne l'emoji correspondant a un resultat humain.

    Args:
        resultat: Le type de resultat humain

    Returns:
        L'emoji correspondant, ou "⚪" si inconnu
    """
    return RESULTAT_EMOJI.get(resultat, "⚪")
