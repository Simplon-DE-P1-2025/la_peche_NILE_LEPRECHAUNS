




## Explications des checks

l'utilisation de la librairie pandera permet de mettre en place les critères de validation des données

### Données du fichiers "flotteurs.csv"

| Colonne                  | Check proposé                                  | Pourquoi                        |
| ------------------------ | ---------------------------------------------- | ------------------------------- |
| `operation_id`           | `pa.Int`, `nullable=False`                     | Identifiant unique, obligatoire |
| `numero_ordre`           | `pa.Int`, `Check.greater_than(0)`              | Doit être positif               |
| `pavillon`               | `Check.isin(["Français","Étranger"])`          | Valeurs valides seulement       |
| `resultat_flotteur`      | `Check.isin([...])`                            | Liste des statuts connus        |
| `type_flotteur`          | `Check.isin([...])`                            | Types valides seulement         |
| `categorie_flotteur`     | `Check.isin(["Pêche","Plaisance","Commerce"])` | Catégories correctes            |
| `numero_immatriculation` | nullable=True                                  | Peut être vide                  |

### Données du fichiers "operation_stats.csv"

| Colonne                                                           | Check proposé                                                                                                                             | Pourquoi                        |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `operation_id`                                                    | `pa.Int`, `nullable=False`, `unique=True`                                                                                                 | Identifiant unique, obligatoire |
| `date`                                                            | `pa.DateTime`, `nullable=False`                                                                                                           | Doit être une date valide       |
| `annee`                                                           | `pa.Int`, `Check(lambda x: x > 2000)`                                                                                                     | Année réaliste                  |
| `mois`                                                            | `pa.Int`, `Check(lambda x: 1 <= x <= 12)`                                                                                                 | Mois valide                     |
| `jour`                                                            | `pa.Int`, `Check(lambda x: 1 <= x <= 31)`                                                                                                 | Jour valide                     |
| `mois_texte`                                                      | `pa.String`, `Check.isin(["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"])` | Nom du mois cohérent            |
| `semaine`                                                         | `pa.Int`, `Check(lambda x: 1 <= x <= 53)`                                                                                                 | Semaine valide                  |
| `annee_semaine`                                                   | `pa.String`                                                                                                                               | Format `YYYY-SS`                |
| `jour_semaine`                                                    | `pa.String`, `Check.isin(["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"])`                                            | Jour de semaine valide          |
| `est_weekend`                                                     | `pa.Bool()`                                                                                                                               | True/False                      |
| `est_jour_ferie`                                                  | `pa.Bool()`                                                                                                                               | True/False                      |
| `est_vacances_scolaires`                                          | `pa.Bool()`                                                                                                                               | True/False                      |
| `phase_journee`                                                   | `pa.String`, `Check.isin(["matinée","après-midi","nuit","déjeuner",""])`                                                                  | Phase de la journée             |
| `concerne_plongee`                                                | `pa.Bool()`                                                                                                                               | True/False                      |
| `implique_wingfoil`                                               | `pa.Bool()`                                                                                                                               | True/False                      |
| `avec_clandestins`                                                | `pa.Bool()`                                                                                                                               | True/False                      |
| `distance_cote_metres`                                            | `pa.Float`, `Check(lambda x: x >= 0)`                                                                                                     | Distance ≥ 0                    |
| `distance_cote_milles_nautiques`                                  | `pa.Float`, `Check(lambda x: x >= 0)`                                                                                                     | Distance ≥ 0                    |
| `est_dans_stm`                                                    | `pa.Bool()`                                                                                                                               | True/False                      |
| `nom_stm`                                                         | `pa.String`, `nullable=True`                                                                                                              | Peut être vide                  |
| `est_dans_dst`                                                    | `pa.Bool()`                                                                                                                               | True/False                      |
| `nom_dst`                                                         | `pa.String`, `nullable=True`                                                                                                              | Peut être vide                  |
| `prefecture_maritime`                                             | `pa.String`, `nullable=True`                                                                                                              | Peut être vide                  |
| `maree_port`                                                      | `pa.String`, `nullable=True`                                                                                                              | Peut être vide                  |
| `maree_coefficient`                                               | `pa.Int`, `Check(lambda x: (0 <= x <= 120))`, `nullable=True`                                                                             | Coefficient réaliste            |
| `maree_categorie`                                                 | `pa.String`, `nullable=True`                                                                                                              | Catégorie de marée              |
| `nombre_personnes_blessees`                                       | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_assistees`                                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees`                                       | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees_accidentellement`                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees_naturellement`                         | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_disparues`                                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_impliquees_dans_fausse_alerte`                  | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_retrouvees`                                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_secourues`                                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tirees_daffaire_seule`                          | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tous_deces`                                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tous_deces_ou_disparues`                        | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_impliquees`                                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_blessees_sans_clandestins`                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_assistees_sans_clandestins`                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees_sans_clandestins`                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees_accidentellement_sans_clandestins`     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_decedees_naturellement_sans_clandestins`        | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_disparues_sans_clandestins`                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_impliquees_dans_fausse_alerte_sans_clandestins` | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_retrouvees_sans_clandestins`                    | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_secourues_sans_clandestins`                     | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tirees_daffaire_seule_sans_clandestins`         | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tous_deces_sans_clandestins`                    | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_tous_deces_ou_disparues_sans_clandestins`       | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_personnes_impliquees_sans_clandestins`                    | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_commerce_impliques`                             | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_peche_impliques`                                | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_impliques`                            | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_loisirs_nautiques_impliques`                    | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_aeronefs_impliques`                                       | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_autre_impliques`                                | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_annexe_impliques`                               | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_autre_loisir_nautique_impliques`                | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_canoe_kayak_aviron_impliques`                   | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_engin_de_plage_impliques`                       | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_kitesurf_impliques`                             | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_voile_legere_impliques`               | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_a_moteur_impliques`                   | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_a_moteur_moins_8m_impliques`          | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_a_moteur_plus_8m_impliques`           | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_plaisance_a_voile_impliques`                    | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_planche_a_voile_impliques`                      | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_ski_nautique_impliques`                         | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_surf_impliques`                                 | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `nombre_flotteurs_vehicule_nautique_a_moteur_impliques`           | `pa.Int`, `Check(lambda x: x >= 0)`                                                                                                       | ≥0                              |
| `sans_flotteur_implique`                                          | `pa.Bool()`                                                                                                                               | True/False                      |

### Données du fichiers "operation.csv"

| Colonne                       | Check proposé         | Pourquoi                                         |
| ----------------------------- | --------------------- | ------------------------------------------------ |
| `operation_id`                | `Int, unique`         | Identifiant unique, obligatoire                  |
| `type_operation`              | `Str, non vide`       | Type d’opération (MAS, SAR, DIV…)                |
| `pourquoi_alerte`             | `Str, nullable`       | Explication facultative                          |
| `moyen_alerte`                | `Str, non vide`       | Moyen utilisé pour alerter                       |
| `qui_alerte`                  | `Str, non vide`       | Qui a donné l’alerte                             |
| `categorie_qui_alerte`        | `Str, non vide`       | Catégorie de l’alerteur                          |
| `cross`                       | `Str, non vide`       | Centre opérationnel (CROSS, Nouvelle-Calédonie…) |
| `departement`                 | `Str, nullable`       | Département ou territoire                        |
| `est_metropolitain`           | `Bool`                | True/False                                       |
| `evenement`                   | `Str, non vide`       | Nom de l’événement                               |
| `categorie_evenement`         | `Str, non vide`       | Catégorie de l’événement                         |
| `autorite`                    | `Str, non vide`       | Autorité principale                              |
| `seconde_autorite`            | `Str, nullable`       | Autorité secondaire                              |
| `zone_responsabilite`         | `Str, nullable`       | Zone de responsabilité                           |
| `latitude`                    | `Float -90 à 90`      | Coordonnée géographique                          |
| `longitude`                   | `Float -180 à 180`    | Coordonnée géographique                          |
| `vent_direction`              | `Int 0–360, nullable` | Direction du vent en degrés                      |
| `vent_direction_categorie`    | `Str, nullable`       | Nom de la direction du vent                      |
| `vent_force`                  | `Int ≥0, nullable`    | Force du vent                                    |
| `mer_force`                   | `Int ≥0, nullable`    | Force de la mer                                  |
| `date_heure_reception_alerte` | `DateTime, non vide`  | Date/heure de réception de l’alerte              |
| `date_heure_fin_operation`    | `DateTime, nullable`  | Date/heure de fin de l’opération                 |
| `numero_sitrep`               | `Int ≥0`              | Numéro du Sitrep                                 |
| `cross_sitrep`                | `Str, non vide`       | Sitrep du CROSS                                  |
| `fuseau_horaire`              | `Str, non vide`       | Fuseau horaire                                   |
| `systeme_source`              | `Str, non vide`       | Système source de l’alerte                       |

### Données du fichiers "resultats_humain.csv"

| Colonne              | Check proposé   | Pourquoi                                                       |
| -------------------- | --------------- | -------------------------------------------------------------- |
| `operation_id`       | `Int, non nul`  | Identifiant d’opération                                        |
| `categorie_personne` | `Str, non vide` | Catégorie de la personne (Pêcheur, Marin, Plaisancier, Autre…) |
| `resultat_humain`    | `Str, non vide` | Type de résultat humain (assistance, secouru, fausse alerte…)  |
| `nombre`             | `Int ≥0`        | Nombre de personnes concernées                                 |
| `dont_nombre_blesse` | `Int ≥0`        | Nombre de blessés (≤ nombre)                                   |
