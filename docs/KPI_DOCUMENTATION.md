# Documentation des KPIs SECMAR

Ce document décrit l'ensemble des KPIs (Key Performance Indicators) implémentés dans le système d'analyse SECMAR, leur origine, leur formule de calcul et leur interprétation.

---

## Table des matières

0. [Choix Métier - Définition Officielle SECMAR](#0-choix-métier---définition-officielle-secmar)
1. [KPIs de Sécurité Maritime](#1-kpis-de-sécurité-maritime)
2. [KPIs de Performance CROSS](#2-kpis-de-performance-cross)
3. [KPIs par Type de Flotteur](#3-kpis-par-type-de-flotteur)
4. [KPIs Géographiques](#4-kpis-géographiques)
5. [KPIs Temporels et Saisonnalité](#5-kpis-temporels-et-saisonnalité)
6. [KPIs Météorologiques](#6-kpis-météorologiques)
7. [KPIs d'Alerte et Anomalies](#7-kpis-dalerte-et-anomalies)
8. [KPIs Year-over-Year](#8-kpis-year-over-year)

---

## 0. Choix Métier - Définition Officielle SECMAR

### Source Réglementaire

Les indicateurs de performance des opérations de sauvetage maritime en France sont définis par le **Programme 205** du Budget de l'État, géré par la Direction des Affaires Maritimes (DAM).

**Sources officielles :**
- [Budget.gouv.fr - Objectifs et indicateurs de performance](https://www.budget.gouv.fr/files/uploads/extract/2020/PLF/BG/PGM/205/FR_2020_PLF_BG_PGM_205_PERF.html)
- [Performance publique - Programme 205](https://www.performance-publique.budget.gouv.fr/sites/performance_publique/files/farandole/ressources/2015/pap/html/DBGPGMOBJINDPGM205.htm)

### KPI Principal : Taux de personnes saines et sauves

#### Définition Officielle

> *"Le numérateur correspond au nombre de personnes mises hors de danger par le dispositif « recherche et sauvetage » coordonné par les CROSS ; le dénominateur correspond au nombre de personnes impliquées dans un accident maritime."*
>
> *"Les personnes mises hors de danger (saines et sauves) sont les personnes retrouvées, assistées et secourues (catégories SECMAR). Les personnes prises en compte par le dispositif sont les personnes retrouvées, secourues, disparues ou décédées."*
>
> *"Les personnes sorties d'affaire par leurs propres moyens ne sont pas prises en compte."*

#### Formule Officielle

```
Taux de personnes saines et sauves = Numérateur / Dénominateur × 100
```

| Élément | Catégories SECMAR incluses |
|---------|---------------------------|
| **Numérateur** (Saines et sauves) | `Personne secourue` + `Personne assistée` + `Personne retrouvée` |
| **Dénominateur** (Prises en compte) | `Personne secourue` + `Personne assistée` + `Personne retrouvée` + `Personne disparue` + `Personne décédée` (toutes catégories) |

#### Exclusions Officielles

Les catégories suivantes sont **exclues** du calcul du KPI officiel :

| Catégorie | Raison de l'exclusion |
|-----------|----------------------|
| `Personne tirée d'affaire seule` | Autonome - n'a pas nécessité l'intervention SAR |
| `Personne impliquée dans fausse alerte` | Pas de situation de détresse réelle |
| `Personne indemne` | Statut non qualifié pour l'indicateur |
| `Inconnu` | Résultat non déterminé |
| `Personne blessée` | Comptabilisé via `dont_nombre_blesse` |
| `Personne malade` | Cas médical, pas SAR |

### Implémentation dans le système

#### Vue SQL `operations_stats`

La vue `operations_stats` fournit les métriques de base pour tous les calculs KPI :

```sql
-- Colonnes officielles SECMAR
nombre_saines_sauves      -- Numérateur : secourues + assistées + retrouvées
nombre_prises_en_compte   -- Dénominateur : saines_sauves + disparues + décédées

-- Colonnes détaillées
nombre_secourues          -- Personne secourue
nombre_assistees          -- Personne assistée
nombre_retrouvees         -- Personne retrouvée
nombre_decedes            -- Tous types de décès
nombre_disparus           -- Personne disparue
nombre_blesses            -- Via dont_nombre_blesse
nombre_tirees_affaire_seule  -- Autonomes (exclues du KPI)
nombre_impliques          -- Total toutes catégories
nombre_fausses_alertes    -- Fausses alertes (exclues du KPI)
```

#### Calcul du KPI Principal

```sql
-- KPI OFFICIEL SECMAR
taux_saines_sauves = nombre_saines_sauves / nombre_prises_en_compte × 100
```

### Objectif de Performance

Selon les rapports annuels de la DAM, l'objectif est de **maintenir ce taux à un niveau élevé** (généralement > 98%).

> *"Cet indicateur porte sur l'engagement du responsable de programme à maintenir la part de personnes saines et sauves à un niveau élevé lors d'une opération de sauvetage dirigée par les CROSS."*

### Données Actuelles du Système

Avec les données SECMAR chargées : (à mettre jour avec les données complètes)

| Métrique | Valeur |
|----------|--------|
| Saines et sauves | 20 567 |
| Prises en compte | 20 895 |
| **Taux officiel** | **98.43%** |

---

## 1. KPIs de Sécurité Maritime

Ces KPIs mesurent l'efficacité des opérations de sauvetage en termes de vies sauvées et de gravité des incidents.

### 1.1 Taux de Personnes Saines et Sauves (KPI Officiel)

| Attribut | Valeur |
|----------|--------|
| **Nom** | Taux de personnes saines et sauves |
| **Description** | Pourcentage de personnes mises hors de danger par le dispositif SAR (définition officielle Programme 205) |
| **Formule** | `(nombre_saines_sauves / nombre_prises_en_compte) × 100` |
| **Unité** | Pourcentage (%) |
| **Objectif** | ≥ 98% (objectif officiel DAM) |
| **Source données** | Vue `operations_stats` (colonnes `nombre_saines_sauves`, `nombre_prises_en_compte`) |
| **Table origine** | `resultats_humain` agrégée par `operation_id` |
| **Vue SQL** | `v_kpi_securite_mensuel.taux_saines_sauves` |
| **Interprétation** | 🟢 ≥98% (Objectif atteint) \| 🟡 95-98% (Attention) \| 🔴 <95% (Critique) |

**Détail des catégories incluses :**
- **Numérateur** : `Personne secourue` + `Personne assistée` + `Personne retrouvée`
- **Dénominateur** : Numérateur + `Personne disparue` + `Personne décédée` (toutes catégories)
- **Exclues** : `Personne tirée d'affaire seule`, `Fausse alerte`, `Inconnu`, `Indemne`

**Requête SQL source :**
```sql
SELECT
    ROUND(SUM(nombre_saines_sauves)::NUMERIC / NULLIF(SUM(nombre_prises_en_compte), 0) * 100, 2)
    AS taux_saines_sauves
FROM operations_stats
```

---

### 1.2 Taux de Mortalité

| Attribut | Valeur |
|----------|--------|
| **Nom** | Taux de mortalité |
| **Description** | Pourcentage de personnes décédées par rapport aux personnes prises en compte par le dispositif SAR |
| **Formule** | `(nombre_decedes / nombre_prises_en_compte) × 100` |
| **Unité** | Pourcentage (%) |
| **Objectif** | < 2% |
| **Source données** | Vue `operations_stats` (colonnes `nombre_decedes`, `nombre_prises_en_compte`) |
| **Table origine** | `resultats_humain` où `resultat_humain IN ('Personne décédée', 'Personne décédée accidentellement', 'Personne décédée naturellement')` |
| **Vue SQL** | `v_kpi_securite_mensuel.taux_mortalite` |
| **Interprétation** | 🟢 ≤1% (Normal) \| 🟡 1-2% (Élevé) \| 🔴 >2% (Critique) |

**Note métier** : Ce taux est calculé sur la base des personnes prises en compte (excluant les autonomes et fausses alertes) pour être cohérent avec le KPI officiel.

---

### 1.3 Taux de Disparition

| Attribut | Valeur |
|----------|--------|
| **Nom** | Taux de disparition |
| **Description** | Pourcentage de personnes disparues (non retrouvées) |
| **Formule** | `(nombre_disparus / nombre_impliques) × 100` |
| **Unité** | Pourcentage (%) |
| **Source données** | Vue `operations_stats` (colonnes `nombre_disparus`, `nombre_impliques`) |
| **Table origine** | `resultats_humain` où `resultat_humain IN ('Personne disparue', 'Disparu')` |
| **Vue SQL** | `v_kpi_securite_mensuel.taux_disparition` |

---

### 1.4 Lives Saved (Vies Sauvées)

| Attribut | Valeur |
|----------|--------|
| **Nom** | Lives Saved |
| **Description** | Nombre total cumulé de personnes sauvées (standard USCG/IMO) |
| **Formule** | `SUM(nombre_sauves)` |
| **Unité** | Nombre absolu |
| **Référence** | KPI officiel US Coast Guard et IMO pour le reporting SAR |
| **Source données** | Vue `operations_stats.nombre_sauves` |
| **Table origine** | `resultats_humain` où `resultat_humain IN ('Personne secourue', 'Sain et sauf', 'Retrouve')` |
| **Vue SQL** | Agrégation de `v_kpi_securite_mensuel.total_sauves` |

**Contexte international :**
- USCG (FY2020) : 4,286 vies sauvées sur 16,845 cas
- RNLI UK : 146,700+ vies sauvées depuis 1824

---

### 1.5 Indice de Gravité

| Attribut | Valeur |
|----------|--------|
| **Nom** | Indice de gravité composite |
| **Description** | Score pondéré mesurant la sévérité globale des incidents |
| **Formule** | `(nombre_decedes × 3 + nombre_disparus × 2 + nombre_blesses) / nombre_impliques` |
| **Unité** | Score décimal (0 = aucune gravité) |
| **Pondération** | Décès (×3), Disparus (×2), Blessés (×1) |
| **Source données** | Vue `operations_stats` |
| **Vue SQL** | `v_kpi_securite_mensuel.indice_gravite` |
| **Interprétation** | 🟢 ≤0.05 (Faible) \| 🟡 0.05-0.1 (Modéré) \| 🔴 >0.1 (Élevé) |

**Requête SQL :**
```sql
SELECT ROUND(
    (SUM(nombre_decedes) * 3 + SUM(nombre_disparus) * 2 + SUM(nombre_blesses))::NUMERIC
    / NULLIF(SUM(nombre_impliques), 0), 3
) AS indice_gravite
FROM operations_stats
```

---

### 1.6 Taux de Blessure

| Attribut | Valeur |
|----------|--------|
| **Nom** | Taux de blessure |
| **Description** | Pourcentage de personnes blessées |
| **Formule** | `(nombre_blesses / nombre_impliques) × 100` |
| **Unité** | Pourcentage (%) |
| **Source données** | Vue `operations_stats.nombre_blesses` |
| **Table origine** | `resultats_humain.dont_nombre_blesse` |
| **Vue SQL** | `v_kpi_securite_mensuel.taux_blessure` |

---

## 2. KPIs de Performance CROSS

Ces KPIs mesurent l'efficacité opérationnelle des Centres Régionaux Opérationnels de Surveillance et de Sauvetage.

### 2.1 Durée Moyenne d'Intervention

| Attribut | Valeur |
|----------|--------|
| **Nom** | Durée moyenne d'intervention |
| **Description** | Temps moyen entre la réception de l'alerte et la fin de l'opération |
| **Formule** | `AVG(date_heure_fin_operation - date_heure_reception_alerte)` |
| **Unité** | Heures |
| **Source données** | Table `operations` (colonnes temporelles) |
| **Vue SQL** | `v_kpi_cross_benchmark.duree_moyenne_heures` |

**Requête SQL :**
```sql
SELECT AVG(
    EXTRACT(EPOCH FROM (date_heure_fin_operation - date_heure_reception_alerte)) / 3600
) AS duree_moyenne_heures
FROM operations
WHERE date_heure_fin_operation IS NOT NULL
```

---

### 2.2 Durée Médiane d'Intervention

| Attribut | Valeur |
|----------|--------|
| **Nom** | Durée médiane d'intervention |
| **Description** | Médiane des durées (plus robuste aux valeurs extrêmes) |
| **Formule** | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY durée)` |
| **Unité** | Heures |
| **Référence** | Standard USCG : objectif < 30 minutes pour la première réponse |
| **Source données** | Table `operations` |
| **Vue SQL** | `v_kpi_cross_benchmark.duree_mediane_heures` |

---

### 2.3 Opérations par Jour

| Attribut | Valeur |
|----------|--------|
| **Nom** | Charge de travail quotidienne |
| **Description** | Nombre moyen d'opérations par jour pour un CROSS |
| **Formule** | `COUNT(operations) / nombre_jours_activite` |
| **Unité** | Opérations/jour |
| **Source données** | Table `operations` agrégée par CROSS |
| **Vue SQL** | `v_kpi_cross_benchmark.operations_par_jour` |

---

### 2.4 Rankings CROSS

| Attribut | Valeur |
|----------|--------|
| **Nom** | Rankings CROSS |
| **Description** | Classement des CROSS selon différentes métriques |
| **Métriques** | Volume (nb opérations), Sauvetage (taux), Rapidité (durée médiane) |
| **Formule** | `RANK() OVER (ORDER BY métrique)` |
| **Source données** | Vue `v_kpi_cross_benchmark` |
| **Colonnes** | `rank_volume`, `rank_sauvetage`, `rank_rapidite` |

---

### 2.5 Personnes par Opération

| Attribut | Valeur |
|----------|--------|
| **Nom** | Ratio personnes/opération |
| **Description** | Nombre moyen de personnes impliquées par opération |
| **Formule** | `SUM(nombre_impliques) / COUNT(operations)` |
| **Unité** | Personnes/opération |
| **Source données** | Tables `operations` + `operations_stats` |
| **Vue SQL** | `v_kpi_cross_benchmark.personnes_par_operation` |

---

## 3. KPIs par Type de Flotteur

Ces KPIs analysent les incidents par catégorie et type d'embarcation.

### 3.1 Répartition par Catégorie

| Attribut | Valeur |
|----------|--------|
| **Nom** | Part de marché par catégorie |
| **Description** | Pourcentage d'opérations par catégorie de flotteur |
| **Formule** | `COUNT(operations_categorie) / COUNT(total) × 100` |
| **Catégories** | Pêche, Plaisance, Commerce, Loisir nautique, Autre |
| **Source données** | Table `flotteurs.categorie_flotteur` |
| **Vue SQL** | `v_kpi_flotteurs_analyse.pct_operations` |

---

### 3.2 Taux de Mortalité par Type

| Attribut | Valeur |
|----------|--------|
| **Nom** | Taux de mortalité sectoriel |
| **Description** | Taux de mortalité spécifique à chaque type de flotteur |
| **Formule** | `SUM(decedes_type) / SUM(impliques_type) × 100` |
| **Source données** | Tables `flotteurs` + `operations_stats` jointes |
| **Vue SQL** | `v_kpi_flotteurs_analyse.taux_mortalite` |
| **Usage** | Identifier les secteurs à risque (pêche vs plaisance) |

---

### 3.3 Distance Côte Moyenne

| Attribut | Valeur |
|----------|--------|
| **Nom** | Distance côte moyenne par type |
| **Description** | Éloignement moyen des incidents par type de flotteur |
| **Formule** | `AVG(distance_cote_metres)` |
| **Unité** | Mètres (ou milles nautiques) |
| **Source données** | Table `operations.distance_cote_metres` |
| **Vue SQL** | `v_kpi_flotteurs_analyse.distance_cote_moyenne_m` |
| **Usage** | Profil offshore/côtier par secteur |

---

### 3.4 Résultat Flotteur Dominant

| Attribut | Valeur |
|----------|--------|
| **Nom** | Distribution des résultats flotteurs |
| **Description** | Répartition des issues pour les embarcations |
| **Valeurs possibles** | Assisté, Coulé, Échoué, Remorqué, Renfloué, Tiré d'affaire seul, etc. |
| **Source données** | Table `flotteurs.resultat_flotteur` |
| **Vue SQL** | `v_kpi_flotteurs_analyse` groupé par `resultat_flotteur` |

---

## 4. KPIs Géographiques

Ces KPIs analysent la distribution spatiale des opérations.

### 4.1 Répartition par Préfecture Maritime

| Attribut | Valeur |
|----------|--------|
| **Nom** | KPIs par zone maritime |
| **Description** | Agrégation des indicateurs par préfecture |
| **Zones** | Atlantique, Manche et mer du Nord, Méditerranée |
| **Source données** | Table `operations.prefecture_maritime` |
| **Vue SQL** | `v_kpi_geographique` groupé par `prefecture_maritime` |

---

### 4.2 Densité par Département

| Attribut | Valeur |
|----------|--------|
| **Nom** | Concentration départementale |
| **Description** | Nombre d'opérations par département |
| **Source données** | Table `operations.departement` |
| **Vue SQL** | `v_kpi_geographique` groupé par `departement` |

---

### 4.3 Centroïde Géographique

| Attribut | Valeur |
|----------|--------|
| **Nom** | Coordonnées moyennes |
| **Description** | Barycentre des opérations par zone |
| **Formule** | `AVG(latitude)`, `AVG(longitude)` |
| **Source données** | Table `operations` (colonnes `latitude`, `longitude`) |
| **Vue SQL** | `v_kpi_geographique.lat_moyenne`, `lon_moyenne` |

---

### 4.4 Opérations en Zones Spéciales

| Attribut | Valeur |
|----------|--------|
| **Nom** | Incidents STM/DST |
| **Description** | Opérations dans les Services de Trafic Maritime ou Dispositifs de Séparation |
| **Source données** | Table `operations` (colonnes `est_dans_stm`, `est_dans_dst`) |
| **Vue SQL** | `v_kpi_geographique.nb_dans_stm`, `nb_dans_dst` |

---

## 5. KPIs Temporels et Saisonnalité

Ces KPIs analysent les patterns temporels des opérations.

### 5.1 Saisonnalité Mensuelle

| Attribut | Valeur |
|----------|--------|
| **Nom** | Distribution mensuelle |
| **Description** | Nombre d'opérations par mois (identification des pics estivaux) |
| **Source données** | Table `operations.date_heure_reception_alerte` |
| **Extraction** | `EXTRACT(MONTH FROM date_heure_reception_alerte)` |
| **Vue SQL** | `v_kpi_temporel_multidim` groupé par `mois` |
| **Pattern attendu** | Pic en juillet-août (vacances, plaisance) |

---

### 5.2 Impact Vacances Scolaires

| Attribut | Valeur |
|----------|--------|
| **Nom** | Effet vacances scolaires |
| **Description** | Comparaison des KPIs en période de vacances vs hors vacances |
| **Source données** | Table `operations.est_vacances_scolaires` (booléen enrichi) |
| **Vue SQL** | `v_kpi_temporel_multidim` filtré par `est_vacances_scolaires` |
| **Origine enrichissement** | Calendrier scolaire zones A/B/C |

---

### 5.3 Impact Jours Fériés

| Attribut | Valeur |
|----------|--------|
| **Nom** | Effet jours fériés |
| **Description** | Concentration des incidents les jours fériés |
| **Source données** | Table `operations.est_jour_ferie` (booléen enrichi) |
| **Vue SQL** | `v_kpi_temporel_multidim` filtré par `est_jour_ferie` |
| **Origine enrichissement** | Calendrier des jours fériés français |

---

### 5.4 Distribution par Phase du Jour

| Attribut | Valeur |
|----------|--------|
| **Nom** | Répartition jour/nuit |
| **Description** | Distribution des opérations par phase de la journée |
| **Phases** | Nuit, Aube, Matin, Après-midi, Soir, Crépuscule |
| **Source données** | Table `operations.phase_journee` (enrichi) |
| **Vue SQL** | `v_kpi_temporel_multidim` groupé par `phase_journee` |
| **Origine enrichissement** | Calcul astronomique basé sur lat/long et date |

---

## 6. KPIs Météorologiques

Ces KPIs analysent l'impact des conditions météo sur les incidents.

### 6.1 Distribution par Force de Vent

| Attribut | Valeur |
|----------|--------|
| **Nom** | Répartition par échelle Beaufort |
| **Description** | Nombre d'opérations par force de vent |
| **Échelle** | 0-12 (Beaufort) |
| **Source données** | Table `operations.vent_force` |
| **Vue SQL** | `v_kpi_meteo_correlation` groupé par `vent_force` |

**Échelle Beaufort :**
| Force | Description | Vent (km/h) |
|-------|-------------|-------------|
| 0-3 | Calme à légère brise | 0-19 |
| 4-5 | Jolie brise à bonne brise | 20-38 |
| 6-7 | Vent frais à grand frais | 39-61 |
| 8-9 | Coup de vent à fort coup de vent | 62-88 |
| 10-12 | Tempête à ouragan | >88 |

---

### 6.2 Distribution par État de la Mer

| Attribut | Valeur |
|----------|--------|
| **Nom** | Répartition par échelle Douglas |
| **Description** | Nombre d'opérations par état de la mer |
| **Échelle** | 0-9 (Douglas) |
| **Source données** | Table `operations.mer_force` |
| **Vue SQL** | `v_kpi_meteo_correlation` groupé par `mer_force` |

**Échelle Douglas :**
| État | Description | Hauteur vagues (m) |
|------|-------------|-------------------|
| 0-2 | Calme à belle | 0-0.5 |
| 3-4 | Peu agitée à agitée | 0.5-2.5 |
| 5-6 | Forte à très forte | 2.5-6 |
| 7-9 | Grosse à énorme | >6 |

---

### 6.3 Corrélation Météo/Gravité

| Attribut | Valeur |
|----------|--------|
| **Nom** | Matrice vent × mer → gravité |
| **Description** | Indice de gravité croisé par conditions météo |
| **Formule** | Pivot `(vent_force, mer_force) → AVG(indice_gravite)` |
| **Source données** | Tables `operations` + `operations_stats` |
| **Vue SQL** | `v_kpi_meteo_correlation` |
| **Visualisation** | Heatmap |

---

### 6.4 Impact Coefficient de Marée

| Attribut | Valeur |
|----------|--------|
| **Nom** | Effet marée |
| **Description** | Distribution des incidents par catégorie de marée |
| **Catégories** | Morte-eau (20-45), Moyenne (45-95), Vive-eau (95-120) |
| **Source données** | Table `operations` (colonnes `maree_coefficient`, `maree_categorie`) |
| **Vue SQL** | `v_kpi_temporel_multidim` groupé par `maree_categorie` |
| **Origine enrichissement** | API marées (port de référence) |

---

## 7. KPIs d'Alerte et Anomalies

Ces KPIs permettent la détection d'anomalies statistiques.

### 7.1 Z-Score Opérations

| Attribut | Valeur |
|----------|--------|
| **Nom** | Écart-type opérations |
| **Description** | Nombre d'écarts-types par rapport à la moyenne mensuelle |
| **Formule** | `(nb_operations - AVG(nb_operations)) / STDDEV(nb_operations)` |
| **Unité** | Écarts-types (σ) |
| **Source données** | Vue `v_kpi_securite_mensuel` agrégée |
| **Vue SQL** | `v_kpi_alertes_anomalies.zscore_operations` |
| **Seuils** | 🟢 [-1, +1] (Normal) \| 🟡 [±1, ±2] (Attention) \| 🔴 >±2 (Alerte) |

---

### 7.2 Z-Score Victimes

| Attribut | Valeur |
|----------|--------|
| **Nom** | Écart-type victimes |
| **Description** | Anomalie sur le nombre de victimes (décédés + disparus) |
| **Formule** | `(total_victimes - AVG(total_victimes)) / STDDEV(total_victimes)` |
| **Unité** | Écarts-types (σ) |
| **Source données** | Vue `operations_stats` agrégée par mois |
| **Vue SQL** | `v_kpi_alertes_anomalies.zscore_victimes` |

---

### 7.3 Niveau d'Alerte

| Attribut | Valeur |
|----------|--------|
| **Nom** | Classification des alertes |
| **Description** | Catégorisation automatique basée sur les z-scores |
| **Niveaux** | NORMAL, ATTENTION, ALERTE |
| **Règles** | Z > 2 → ALERTE, Z > 1 → ATTENTION, sinon NORMAL |
| **Vue SQL** | `v_kpi_alertes_anomalies.niveau_alerte_victimes`, `niveau_alerte_operations` |

**Requête SQL :**
```sql
SELECT
    CASE
        WHEN zscore_victimes > 2 THEN 'ALERTE'
        WHEN zscore_victimes > 1 THEN 'ATTENTION'
        ELSE 'NORMAL'
    END AS niveau_alerte_victimes
FROM v_kpi_alertes_anomalies
```

---

## 8. KPIs Year-over-Year

Ces KPIs comparent les performances d'une année à l'autre.

### 8.1 Variation Opérations YoY

| Attribut | Valeur |
|----------|--------|
| **Nom** | Évolution annuelle des opérations |
| **Description** | Pourcentage de variation par rapport à l'année précédente |
| **Formule** | `(nb_ops_N - nb_ops_N-1) / nb_ops_N-1 × 100` |
| **Unité** | Pourcentage (%) |
| **Source données** | Vue `v_kpi_yoy_comparison` |
| **Colonne** | `yoy_operations_pct` |

**Requête SQL :**
```sql
SELECT
    annee,
    nb_operations,
    LAG(nb_operations) OVER (ORDER BY annee) AS ops_annee_precedente,
    ROUND(
        (nb_operations - LAG(nb_operations) OVER (ORDER BY annee))::NUMERIC /
        NULLIF(LAG(nb_operations) OVER (ORDER BY annee), 0) * 100, 2
    ) AS yoy_operations_pct
FROM aggregation_annuelle
```

---

### 8.2 Variation Personnes YoY

| Attribut | Valeur |
|----------|--------|
| **Nom** | Évolution annuelle des personnes impliquées |
| **Formule** | `(personnes_N - personnes_N-1) / personnes_N-1 × 100` |
| **Vue SQL** | `v_kpi_yoy_comparison.yoy_personnes_pct` |

---

### 8.3 Variation Lives Saved YoY

| Attribut | Valeur |
|----------|--------|
| **Nom** | Évolution annuelle des personnes sauvées |
| **Formule** | `(sauves_N - sauves_N-1) / sauves_N-1 × 100` |
| **Vue SQL** | `v_kpi_yoy_comparison.yoy_sauves_pct` |
| **Importance** | KPI stratégique aligné standards USCG/IMO |

---

## Annexes

### A. Schéma des tables sources

```
operations (60 colonnes)
├── operation_id (PK)
├── date_heure_reception_alerte
├── date_heure_fin_operation
├── cross, departement, prefecture_maritime
├── latitude, longitude, distance_cote_metres
├── vent_force, mer_force, maree_coefficient
├── est_jour_ferie, est_vacances_scolaires, phase_journee
└── ...

flotteurs (9 colonnes)
├── flotteur_id (PK)
├── operation_id (FK)
├── type_flotteur, categorie_flotteur
├── resultat_flotteur
└── ...

resultats_humain (8 colonnes)
├── resultat_id (PK)
├── operation_id (FK)
├── resultat_humain, nombre, dont_nombre_blesse
└── ...

operations_stats (VIEW calculée)
├── operation_id
├── nombre_decedes, nombre_disparus, nombre_blesses
├── nombre_sauves, nombre_impliques, nombre_assistances
└── ...
```

### B. Liste des vues KPI

| Vue | Description | Fichier |
|-----|-------------|---------|
| `v_kpi_securite_mensuel` | Taux de sécurité par mois | `sql/views_kpi.sql` |
| `v_kpi_cross_benchmark` | Performance CROSS avec ranking | `sql/views_kpi.sql` |
| `v_kpi_flotteurs_analyse` | Stats par type de flotteur | `sql/views_kpi.sql` |
| `v_kpi_temporel_multidim` | Analyse temporelle croisée | `sql/views_kpi.sql` |
| `v_kpi_meteo_correlation` | Corrélations météo/gravité | `sql/views_kpi.sql` |
| `v_kpi_yoy_comparison` | Comparatifs Year-over-Year | `sql/views_kpi.sql` |
| `v_kpi_alertes_anomalies` | Détection anomalies (z-scores) | `sql/views_kpi.sql` |
| `v_kpi_geographique` | Analyse par zone géographique | `sql/views_kpi.sql` |
| `v_kpi_type_operation` | Stats par type d'opération | `sql/views_kpi.sql` |

### C. Standards internationaux de référence

| Organisation | Standard | Valeur |
|--------------|----------|--------|
| USCG | Response Time | < 30 minutes |
| USCG | Lives Saved (FY2020) | 4,286 / 16,845 cas |
| IMO | Golden Hour | Intervention < 1h |
| IMO/SOLAS | Safety Management | ISM Code compliance |
| RNLI UK | Cumul historique | 146,700+ vies |

### D. Fichiers d'implémentation

| Fichier | Contenu |
|---------|---------|
| `sql/views_kpi.sql` | Définition des 9 vues SQL |
| `src/database/kpi_queries.py` | Fonctions Python d'accès aux KPIs |
| `app/pages/6_KPI_Securite.py` | Dashboard sécurité Streamlit |
| `app/pages/7_Performance_CROSS.py` | Dashboard benchmarking CROSS |
| `app/pages/8_Analyse_Flotteurs.py` | Dashboard analyse sectorielle |
| `app/pages/9_Saisonnalite_Meteo.py` | Dashboard temporel/météo |
| `app/pages/10_Alertes_Anomalies.py` | Dashboard alertes |
| `exports/powerbi_data.py` | Script export Power BI |

---

*Document généré le 14 janvier 2026*
