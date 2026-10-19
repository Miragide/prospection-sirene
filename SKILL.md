---
name: prospection-sirene
description: Construit des listes de prospection B2B françaises à partir de la base SIRENE open data (fichiers Parquet data.gouv.fr) — filtrage par zone (communes INSEE, codes postaux, départements, rayon en km autour d'un code postal), secteur (codes NAF), taille et forme juridique, puis priorisation et export CSV lisible dans Excel avec rapport de répartition. Utilise ce skill dès qu'on parle de lister/extraire/cibler des entreprises françaises d'une zone ou d'un secteur, de fichier de prospection, de SIRENE/SIRET/SIREN, de codes NAF, de recruter des adhérents pour un club d'entrepreneurs ou une fédération, de trouver des artisans/PME/TPE autour d'une ville, ou de préparer une campagne email/SMS B2B locale — même si le mot "SIRENE" n'est pas prononcé.
---

# Prospection B2B à partir de SIRENE

Ce skill sert à livrer, pour un client (club d'entrepreneurs, fédération, indépendant qui cherche des clients…), une **liste propre d'entreprises actives** sur une zone et un secteur, puis à accompagner la suite : validation commerciale, enrichissement des contacts, campagne.

Le cœur technique est déjà écrit et testé : `scripts/filtrer_sirene.py` lit les fichiers SIRENE en Parquet avec des filtres poussés au niveau du fichier (quelques secondes sur ~2,8 Go), joint établissements et unités légales, et produit un CSV lisible. Ton travail consiste surtout à **traduire la demande du client en fichier de config JSON**, lancer le script, lire le rapport et ajuster.

## Prérequis

- Python 3.10+ avec `pip install pandas pyarrow` (et `pgeocode` si zone par rayon).
- Les deux fichiers SIRENE au format Parquet dans un même dossier :
  `StockEtablissement_utf8.parquet` et `StockUniteLegale_utf8.parquet`.
  S'ils manquent, voir `references/sources_donnees.md` (liens + pourquoi pas l'API).

## Déroulé type

1. **Cadrer la demande** : quelle zone, quels secteurs, quelle taille d'entreprise, quel usage (club = dirigeants locaux ; vendeur de service = cible qui a le besoin). Si la zone est floue ("autour de Saintes"), propose un rayon ou une liste de communes et fais valider.
2. **Écrire la config** JSON (partir d'un exemple de `assets/exemples/`).
3. **Lancer** :
   ```bash
   python scripts/filtrer_sirene.py --config ma_campagne.json --data-dir /chemin/vers/parquets
   ```
4. **Lire le rapport** imprimé (tailles, formes juridiques, top activités, communes) et ajuster. Repères : un volume exploitable pour une campagne locale est souvent de 200 à 3 000 lignes ; si la liste est dominée par des SCI ou des structures non pertinentes, ajoute des exclusions NAF.
5. **Prioriser** si la liste est trop longue pour être enrichie (voir plus bas).
6. **Suite commerciale** : avant tout enrichissement payant, le client valide un échantillon, le message et le devis — voir `references/workflow_commercial.md`.

## Format de config

```json
{
  "nom": "Libellé de la campagne (affiché dans le rapport)",
  "zone": { "communes_insee": ["17415"] },
  "naf_inclus": ["@artisanat_batiment", "56.10A"],
  "naf_exclus": ["@non_entreprises"],
  "effectifs": ["NN", "00", "01", "02", "03", "11", "12"],
  "groupes_naf": { "Bâtiment": "@artisanat_batiment" },
  "sieges_uniquement": true,
  "exclure_non_entreprises": true,
  "sortie": "data/ma_campagne.csv"
}
```

Seule `zone` est obligatoire. Détail des clés :

- **zone** — une ou plusieurs de ces clés (combinées en ET) :
  - `communes_insee` : codes commune INSEE à 5 chiffres (≠ code postal ; Saintes = `17415`, code postal 17100). Plusieurs communes partagent souvent un code postal et une commune peut en avoir plusieurs.
  - `codes_postaux` : liste de codes postaux.
  - `departements` : `["08", "10", …]` (2 premiers caractères du code commune ; Corse = `2A`/`2B`).
  - `rayon` : `{"centre": "89400", "km": 50}` — calcule les codes postaux à vol d'oiseau via `scripts/cercle_geographique.py` (nécessite `pgeocode`, qui télécharge la base GeoNames au premier appel). Le cercle déborde volontiers sur les départements voisins, c'est voulu.
- **naf_inclus / naf_exclus** — codes NAF au format `"43.21A"`, ou groupes prédéfinis préfixés par `@` (liste dans `assets/naf_presets.json` : `artisanat_batiment`, `artisanat_fabrication_reparation`, `artisanat_alimentaire`, `artisanat_services`, `agriculture_hors_vigne`, `industrie_alimentaire`, `boissons`, `non_entreprises`). Tu peux ajouter des groupes dans ce fichier pour une nouvelle cible. Sans `naf_inclus`, tous les secteurs sont pris.
- **effectifs** — tranches INSEE à garder : `NN` non renseigné, `00` 0 salarié, `01` 1–2, `02` 3–5, `03` 6–9, `11` 10–19, `12` 20–49, `21` 50–99, `22` 100–199, `31`… `53` au-delà. Sans cette clé, toutes les tailles. Attention : `NN` représente souvent 80 % des établissements d'une zone (micro-entrepreneurs, EI) — l'exclure réduit fortement le volume.
- **groupes_naf** — optionnel, ajoute une colonne `Domaine` (libellé → preset ou liste de codes) et une répartition par domaine dans le rapport.
- **sieges_uniquement** (défaut `true`) — on garde le siège, là où se trouve le décideur. Mettre `false` pour compter aussi les agences/succursales locales de groupes.
- **exclure_non_entreprises** (défaut `true`) — retire associations, fondations, syndicats de copropriété (catégories juridiques 9100–9999) et indivisions (2100–2199).

## Le CSV produit

Encodé `utf-8-sig` pour que les accents s'affichent dans Excel. Colonnes : `Nom` (enseigne > raison sociale > Prénom NOM), `Dirigeant (EI)` (rempli seulement pour les entrepreneurs individuels — SIRENE ne donne pas le dirigeant des sociétés), `Forme juridique`, `Domaine` (si `groupes_naf`), `Activité`, `Code NAF`, `Adresse`, `Code postal`, `Commune`, `Département`, `Taille`, `Date création`, `SIRET`.

Les libellés NAF viennent de `assets/libelles.json`, qui ne couvre que ~200 codes utilisés jusqu'ici ; un code sans libellé s'affiche tel quel dans `Activité`. Si la cible touche d'autres secteurs, complète ce fichier (nomenclature NAF rév. 2 sur insee.fr) plutôt que de livrer des codes bruts au client.

## Prioriser une liste trop longue

L'enrichissement des contacts coûte par ligne : on ne l'applique qu'aux profils les plus pertinents.

```bash
python scripts/prioriser.py data/liste.csv data/liste_prioritaire.csv \
    --tailles "Non renseigné" "0 salarié" "1–2 salariés" --anciennete-max 5
```

`--tailles` prend les libellés exacts de la colonne `Taille` (le script prévient si une valeur n'existe pas). `--anciennete-max/--anciennete-min` filtrent sur la date de création (les lignes sans date sont alors exclues). Choisis les critères selon la logique du client et explique-la-lui : par exemple, une assistante administrative cible les très petites structures récentes (pas encore de personnel administratif) ; un club d'entrepreneurs gagne à commencer par les entreprises avec salariés (activité visible, contact trouvable dans 75–85 % des cas, contre ~50 % sur l'ensemble).

## Exemples de campagnes réelles

Dans `assets/exemples/` — chacune reproduit exactement une liste déjà livrée :

| Fichier | Cible | Volume |
|---|---|---|
| `saintes_club_entrepreneurs.json` | Toutes TPE/PME de Saintes (commune INSEE), hors SCI/associations/administrations | 3 792 |
| `grandest_agroalimentaire.json` | Agriculture + industrie alimentaire hors boissons, 10 départements, ≥ 3 salariés | 3 183 |
| `yonne_artisans_rayon50km.json` | Artisans (4 domaines) dans 50 km autour de Cheny, toutes tailles | 9 219 |

## Pièges connus

- Dans le Parquet, `etablissementSiege` est un **booléen** (pas `'O'`/`'N'` comme dans le CSV) et `categorieJuridiqueUniteLegale` est un entier. Le script gère déjà ces types ; à garder en tête si tu écris une requête à la main.
- Ne charge jamais un fichier entier dans pandas pour filtrer ensuite : passe par les filtres PyArrow (`pyarrow.dataset` + expression), comme le fait le script.
- Un même code NAF regroupe des métiers différents (69.10Z = avocats **et** notaires) : le libellé est indicatif.
- Le nom du dirigeant d'une société (SARL, SAS…) n'est pas dans SIRENE ; il faut une source tierce (Pappers, annuaire-entreprises.data.gouv.fr) au moment de l'enrichissement.

## Références

- `references/sources_donnees.md` — où télécharger les fichiers, schéma des colonnes utiles, pourquoi ne pas utiliser l'API Recherche d'Entreprises.
- `references/workflow_commercial.md` — étapes du service de bout en bout (cadrage → validation client → enrichissement → campagne → rapport), grille tarifaire, RGPD, retours d'expérience sur l'enrichissement. À lire dès qu'on passe de la liste à la campagne.
