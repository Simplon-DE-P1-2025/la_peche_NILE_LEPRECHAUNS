"""Descriptions officielles SECMAR extraites de la documentation.

Source: https://mtes-mct.github.io/secmar-documentation/schema.html

Ce dictionnaire centralise les descriptions officielles des champs
pour affichage dans le catalogue de donnees.
"""

SECMAR_DESCRIPTIONS = {
    # =========================================================================
    # Operations - Champs principaux
    # =========================================================================
    "operation_id": "Le numero unique de l'operation",
    "type_operation": "Le type d'operation coordonne par le CROSS (SAR, MAS, DIV, SUR, POL)",
    "sous_type_operation": "Sous-categorie du type d'operation",
    "pourquoi_alerte": "Pourquoi l'alerte a-t-elle ete donnee",
    "moyen_alerte": "Comment l'alerte a-t-elle ete donnee (VHF, telephone, etc.)",
    "qui_alerte": "Qui a donne l'alerte",
    "categorie_qui_alerte": "Categorie du lanceur d'alerte",
    "cross": "CROSS en charge de la coordination de l'operation",
    "departement": "Departement ou se deroule l'operation",
    "est_metropolitain": "Indique si l'operation se deroule en France metropolitaine",
    "evenement": "Evenement qui a donne lieu a l'operation",
    "categorie_evenement": "Categorie de l'evenement ayant donne lieu a l'operation",
    "autorite": "Autorite en charge de la coordination de l'operation",
    "seconde_autorite": "Seconde autorite en charge de la coordination",
    "zone_responsabilite": "Ou se situe l'intervention (zone SAR)",
    "latitude": "Coordonnees en format EPSG:4326 WGS84 (-90 a 90)",
    "longitude": "Coordonnees en format EPSG:4326 WGS84 (-180 a 180)",
    "vent_direction": "Direction du vent, en degres (0-360)",
    "vent_direction_categorie": "Nom de la direction du vent (Nord, Sud, etc.)",
    "vent_force": "Force du vent selon l'echelle de Beaufort (0-12)",
    "mer_force": "Etat de la mer selon l'echelle de Douglas (0-9)",
    "date_heure_reception_alerte": "Horodatage de reception de l'alerte en UTC (ISO8601)",
    "date_heure_fin_operation": "Horodatage de fin d'operation en UTC (ISO8601)",
    "numero_sitrep": "Numero de situation report",
    "cross_sitrep": "Identifiant unique de l'operation (CROSS + annee + numero)",
    "fuseau_horaire": "Fuseau horaire du CROSS coordonnant l'operation (IANA)",
    "systeme_source": "Systeme informatique d'ou provient la donnee (SECMAR, SNOSAN)",
    # =========================================================================
    # Operations - Champs enrichis (operations_stats -> operations)
    # =========================================================================
    "est_jour_ferie": "Indique si l'operation se deroule pendant un jour ferie",
    "est_vacances_scolaires": "Indique si l'operation se deroule pendant des vacances scolaires (zone A, B ou C)",
    "phase_journee": "Moment de la journee (matinee, dejeuner, apres-midi ou nuit)",
    "concerne_plongee": "Indique si l'operation concerne une activite de plongee (bouteille, apnee) ou chasse sous-marine",
    "implique_wingfoil": "Indique si l'operation implique au moins 1 wingfoil",
    "distance_cote_metres": "Distance en metres vers la cote ou frontiere terrestre francaise la plus proche",
    "distance_cote_milles_nautiques": "Distance equivalente en milles nautiques",
    "est_dans_stm": "Indique si l'operation se deroule dans une zone de service de trafic maritime (veille renforcee)",
    "nom_stm": "Nom de la zone de service de trafic maritime",
    "est_dans_dst": "Indique si l'operation se deroule dans un dispositif de separation du trafic",
    "nom_dst": "Nom du dispositif de separation du trafic",
    "prefecture_maritime": "Prefecture maritime de rattachement (manche, atlantique ou mediterranee)",
    "maree_port": "Port de reference pour connaitre le coefficient moyen de maree",
    "maree_coefficient": "Coefficient moyen de maree de la journee (entre 20 et 120)",
    "maree_categorie": "Classification du coefficient de maree par plages (20-45, 46-70, 71-95, 96-120)",
    # =========================================================================
    # Flotteurs
    # =========================================================================
    "flotteur_id": "Identifiant unique du flotteur dans la base",
    "numero_ordre": "Ordre d'implication des flotteurs dans l'operation",
    "pavillon": "Indique si le pavillon du flotteur est francais ou etranger",
    "resultat_flotteur": "Etat du flotteur a la fin de l'intervention",
    "type_flotteur": "Type precis du flotteur (voilier, vedette, kayak, etc.)",
    "categorie_flotteur": "Grande categorie a laquelle appartient le flotteur",
    "numero_immatriculation": "Numero d'immatriculation du navire (chiffre pour anonymisation)",
    # =========================================================================
    # Resultats humains
    # =========================================================================
    "resultat_id": "Identifiant unique du resultat humain dans la base",
    "categorie_personne": "Categorie de personne impliquee (Equipage, Passager, Autre, Inconnu)",
    "resultat_humain": "Description du bilan humain (secouru, decede, disparu, etc.)",
    "nombre": "Nombre de personnes impliquees dans ce bilan",
    "dont_nombre_blesse": "Nombre de personnes blessees dans le bilan (sous-ensemble)",
}
