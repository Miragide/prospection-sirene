# Sources de données SIRENE

## Fichiers à télécharger

Page : https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/
Mise à jour mensuelle. Prendre le format **Parquet** (disponible depuis juin 2025), pas le CSV.

| Fichier | Une ligne par | Contient | Taille |
|---|---|---|---|
| `StockEtablissement_utf8.parquet` | établissement (SIRET) | adresse, commune, code postal, état actif/fermé, effectif, siège ou non, NAF, enseigne | ~2,2 Go |
| `StockUniteLegale_utf8.parquet` | unité légale (SIREN) | raison sociale, forme juridique, NAF, nom/prénom du dirigeant (personnes physiques uniquement) | ~0,7 Go |

Jointure : `siren` (les 9 premiers chiffres du SIRET).

Optionnel : [Géolocalisation des établissements SIRENE](https://www.data.gouv.fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques) (lat/lon par SIRET) si un filtre par rayon plus précis que le code postal devient nécessaire.

## Colonnes utiles

### StockEtablissement

| Colonne | Type Parquet | Valeurs |
|---|---|---|
| `etatAdministratifEtablissement` | string | `A` actif, `F` fermé |
| `etablissementSiege` | **bool** | `True` = siège |
| `codeCommuneEtablissement` | string | code INSEE 5 caractères (Saintes = `17415`) |
| `codePostalEtablissement` | string | code postal (≠ code INSEE) |
| `libelleCommuneEtablissement` | string | nom de commune en majuscules |
| `numeroVoieEtablissement`, `typeVoieEtablissement`, `libelleVoieEtablissement`, `complementAdresseEtablissement` | string | adresse |
| `activitePrincipaleEtablissement` | string | NAF rév. 2, format `43.21A` |
| `trancheEffectifsEtablissement` | string | `NN`, `00`, `01`, `02`, `03`, `11`, `12`, `21`… `53` |
| `dateCreationEtablissement` | date | |
| `enseigne1Etablissement`, `denominationUsuelleEtablissement` | string | nom commercial |
| `activitePrincipaleNAF25Etablissement` | string | future nomenclature NAF 2025 (pas encore utilisée par les scripts) |

### StockUniteLegale

| Colonne | Type Parquet | Notes |
|---|---|---|
| `denominationUniteLegale` | string | raison sociale des personnes morales |
| `nomUniteLegale`, `prenom1UniteLegale` | string | uniquement pour les entrepreneurs individuels |
| `categorieJuridiqueUniteLegale` | **int64** | 1000 = EI, 5499 = société civile (SCI…), 5710 = SAS, 6540 = SARL, 92xx = associations |
| `activitePrincipaleUniteLegale` | string | NAF de l'unité légale |

## Pourquoi pas l'API Recherche d'Entreprises

`recherche-entreprises.api.gouv.fr` est faite pour chercher une entreprise par nom, pas pour extraire une zone entière :

- 7 requêtes/s, 25 résultats par page ;
- plafond Elasticsearch d'environ 10 000 résultats par requête — bloquant dès qu'on élargit la zone ;
- entreprises non diffusibles absentes.

Les fichiers Parquet locaux n'ont aucune de ces limites et un filtrage complet prend quelques secondes.

## Vérifications manuelles

https://annuaire-entreprises.data.gouv.fr/ permet de vérifier une entreprise, trouver un code commune INSEE ou estimer un volume avant de lancer le script.
