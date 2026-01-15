# KPIs PowerBI - Tableau de Bord Décideurs

> Documentation technique pour l'export des données SECMAR vers PowerBI
> Audience : Direction, Préfets maritimes, Ministère de la Mer

---

## 1. Taux de Personnes Saines et Sauves (KPI Officiel)

### Objectif
Indicateur principal du Programme 205 du Budget de l'État français. Mesure l'efficacité globale du dispositif SAR (Search and Rescue).

### Cible
**> 98%** (objectif national)

### Formule officielle
```
Taux S&S = (Personnes saines et sauves / Personnes prises en compte) × 100
```

### Définitions
- **Numérateur** : `Personne secourue` + `Personne assistée` + `Personne retrouvée`
- **Dénominateur** : Numérateur + `Personne disparue` + `Personne décédée` (toutes causes)
- **Exclusions** : `Personne tirée d'affaire seule`, fausses alertes, inconnu

### SQL
```sql
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte) as annee,
    SUM(s.nombre_saines_sauves) as total_saines_sauves,
    SUM(s.nombre_prises_en_compte) as total_prises_en_compte,
    ROUND(
        100.0 * SUM(s.nombre_saines_sauves) / NULLIF(SUM(s.nombre_prises_en_compte), 0),
        2
    ) as taux_saines_sauves
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
ORDER BY annee;
```

### Visualisation recommandée
- **Gauge** avec seuils : Rouge < 95%, Jaune 95-98%, Vert > 98%
- **Ligne temporelle** sur 5 ans pour tendance

---

## 2. Évolution Annuelle du Taux S&S

### Objectif
Suivre la tendance long terme et détecter les dégradations de performance.

### Cible
Tendance stable ou en hausse sur 5 ans.

### SQL
```sql
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte) as annee,
    COUNT(*) as nb_operations,
    SUM(s.nombre_saines_sauves) as saines_sauves,
    SUM(s.nombre_prises_en_compte) as prises_en_compte,
    SUM(s.nombre_decedes) as decedes,
    SUM(s.nombre_disparus) as disparus,
    ROUND(100.0 * SUM(s.nombre_saines_sauves) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_ss,
    ROUND(100.0 * SUM(s.nombre_decedes) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_mortalite
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte >= CURRENT_DATE - INTERVAL '5 years'
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
ORDER BY annee;
```

### Visualisation recommandée
- **Graphique en ligne** avec annotation des événements majeurs
- **Sparkline** pour résumé exécutif

---

## 3. Benchmark Inter-CROSS

### Objectif
Comparer la performance des 10 CROSS actifs pour identifier les bonnes pratiques et les axes d'amélioration.

### CROSS actifs (2024)
1. Gris-Nez
2. Jobourg
3. Corsen
4. Étel
5. La Garde
6. Corse
7. Antilles-Guyane
8. Polynésie
9. Nouvelle-Calédonie
10. Sud océan Indien

### SQL
```sql
SELECT
    o."cross",
    COUNT(*) as nb_operations,
    SUM(s.nombre_prises_en_compte) as personnes_prises_en_compte,
    SUM(s.nombre_saines_sauves) as saines_sauves,
    SUM(s.nombre_decedes) as decedes,
    ROUND(100.0 * SUM(s.nombre_saines_sauves) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_ss,
    ROUND(100.0 * SUM(s.nombre_decedes) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_mortalite,
    ROUND(AVG(EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte))/3600), 1) as duree_moyenne_h
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o."cross" IN (
    'Gris-Nez', 'Jobourg', 'Corsen', 'Étel', 'Etel', 'La Garde',
    'Corse', 'Antilles-Guyane', 'Polynésie', 'Nouvelle-Calédonie', 'Sud océan Indien'
)
GROUP BY o."cross"
ORDER BY taux_ss DESC;
```

### Visualisation recommandée
- **Bar chart horizontal** classé par taux S&S
- **Tableau matriciel** avec mise en forme conditionnelle
- **Carte** avec bulles proportionnelles au volume

---

## 4. Taux de Mortalité par Secteur d'Activité

### Objectif
Orienter les politiques de prévention vers les secteurs les plus à risque.

### Secteurs clés
- Pêche professionnelle
- Plaisance
- Sports nautiques (kitesurf, paddle, etc.)
- Commerce maritime

### SQL
```sql
SELECT
    f.categorie_flotteur,
    COUNT(DISTINCT o.operation_id) as nb_operations,
    SUM(s.nombre_prises_en_compte) as personnes,
    SUM(s.nombre_decedes) as decedes,
    SUM(s.nombre_disparus) as disparus,
    ROUND(100.0 * SUM(s.nombre_decedes + s.nombre_disparus) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_mortalite,
    ROUND(100.0 * SUM(s.nombre_saines_sauves) / NULLIF(SUM(s.nombre_prises_en_compte), 0), 2) as taux_ss
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
JOIN flotteurs f ON o.operation_id = f.operation_id
WHERE f.categorie_flotteur IS NOT NULL
GROUP BY f.categorie_flotteur
ORDER BY taux_mortalite DESC;
```

### Visualisation recommandée
- **Treemap** avec taille = volume, couleur = taux mortalité
- **Donut chart** pour répartition des décès par secteur

---

## 5. Volume d'Activité Annuel

### Objectif
Suivre la charge opérationnelle globale pour dimensionner les moyens.

### SQL
```sql
SELECT
    EXTRACT(YEAR FROM date_heure_reception_alerte) as annee,
    COUNT(*) as nb_operations,
    COUNT(*) / 365.0 as operations_par_jour,
    SUM(s.nombre_impliques) as personnes_impliquees
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(YEAR FROM date_heure_reception_alerte)
ORDER BY annee;
```

### Visualisation recommandée
- **KPI Card** avec variation N/N-1
- **Histogramme** annuel

---

## 6. Répartition Géographique

### Objectif
Visualiser la concentration des opérations pour optimiser le déploiement des moyens.

### SQL
```sql
SELECT
    o.departement,
    o."cross",
    COUNT(*) as nb_operations,
    SUM(s.nombre_prises_en_compte) as personnes,
    SUM(s.nombre_decedes) as decedes,
    AVG(o.latitude) as lat_moyenne,
    AVG(o.longitude) as lon_moyenne
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.latitude IS NOT NULL AND o.longitude IS NOT NULL
GROUP BY o.departement, o."cross"
ORDER BY nb_operations DESC;
```

### Visualisation recommandée
- **Carte choroplèthe** par département
- **Carte à bulles** avec densité d'opérations

---

## 7. Analyse Saisonnière

### Objectif
Anticiper les pics d'activité pour la planification RH et logistique.

### SQL
```sql
SELECT
    EXTRACT(MONTH FROM date_heure_reception_alerte) as mois,
    TO_CHAR(date_heure_reception_alerte, 'Month') as nom_mois,
    COUNT(*) as nb_operations,
    ROUND(AVG(COUNT(*)) OVER (), 0) as moyenne_mensuelle,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct_annuel
FROM operations
WHERE date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(MONTH FROM date_heure_reception_alerte), TO_CHAR(date_heure_reception_alerte, 'Month')
ORDER BY mois;
```

### Visualisation recommandée
- **Graphique en aire** avec pic estival mis en évidence
- **Heatmap** mois × année

---

## 8. Temps de Réponse Médian par CROSS

### Objectif
Mesurer l'efficacité opérationnelle et identifier les CROSS nécessitant des améliorations.

### SQL
```sql
SELECT
    o."cross",
    COUNT(*) as nb_operations,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte))/3600
    ) as duree_mediane_h,
    ROUND(AVG(EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte))/3600), 1) as duree_moyenne_h
FROM operations o
WHERE o.date_heure_fin_operation IS NOT NULL
  AND o.date_heure_reception_alerte IS NOT NULL
  AND o."cross" IS NOT NULL
GROUP BY o."cross"
ORDER BY duree_mediane_h;
```

### Visualisation recommandée
- **Box plot** par CROSS
- **Bar chart** horizontal avec ligne de référence (objectif)

---

## 9. Évolution des Décès et Disparus

### Objectif
Suivre l'impact des politiques de prévention sur le long terme.

### SQL
```sql
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte) as annee,
    SUM(s.nombre_decedes) as decedes,
    SUM(s.nombre_disparus) as disparus,
    SUM(s.nombre_decedes + s.nombre_disparus) as total_victimes,
    LAG(SUM(s.nombre_decedes + s.nombre_disparus)) OVER (ORDER BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)) as victimes_annee_prec,
    ROUND(
        100.0 * (SUM(s.nombre_decedes + s.nombre_disparus) -
        LAG(SUM(s.nombre_decedes + s.nombre_disparus)) OVER (ORDER BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)))
        / NULLIF(LAG(SUM(s.nombre_decedes + s.nombre_disparus)) OVER (ORDER BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)), 0),
        1
    ) as variation_pct
FROM operations o
JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
ORDER BY annee;
```

### Visualisation recommandée
- **Graphique combiné** : barres (volume) + ligne (tendance)
- **KPI Card** avec flèche de variation

---

## Structure Export PowerBI

### Tables recommandées

| Table | Description | Rafraîchissement |
|-------|-------------|------------------|
| `fact_operations` | Opérations avec métriques | Quotidien |
| `fact_kpi_annuel` | KPIs agrégés par année | Hebdomadaire |
| `fact_kpi_cross` | KPIs par CROSS | Hebdomadaire |
| `dim_cross` | Référentiel CROSS | Mensuel |
| `dim_temps` | Calendrier | Annuel |
| `dim_categorie_flotteur` | Référentiel flotteurs | Mensuel |

### Format d'export
- **CSV** ou **Parquet** pour volumes importants
- Encodage : UTF-8
- Séparateur : point-virgule (;) pour compatibilité Excel FR

---

## Sources

- [Programme 205 - Budget.gouv.fr](https://www.budget.gouv.fr/documentation/documents-budgetaires/exercice-2024/projet-de-loi-de-finances/budget-general/affaires-maritimes)
- Définition officielle SECMAR (Affaires Maritimes)
- Documentation interne CROSS

---

*Document généré le 15/01/2026 - Équipe Data SECMAR*
