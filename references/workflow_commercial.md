# Workflow commercial : de la liste à la campagne

Le service vendu : un fichier de contacts qualifiés + une campagne email/SMS envoyée au nom du client, clé en main, suivie d'un rapport. Cibles idéales : clubs d'entrepreneurs, associations professionnelles, CCI, petites fédérations, réseaux d'artisans — des structures qui recrutent localement sans service marketing.

L'avantage par rapport aux agences nationales : être local et maîtriser la donnée publique SIRENE, trop granulaire pour les gros acteurs.

## Étapes

### 1. Cadrage (sans code)
- Périmètre géographique exact → codes INSEE, codes postaux, départements ou rayon.
- Critères : taille, secteurs à inclure/exclure, formes juridiques à exclure.
- Volume attendu : estimer avec un premier passage du script ; viser un volume exploitable pour le budget.

### 2. Filtrage
`scripts/filtrer_sirene.py` avec la config validée. Ouvrir le CSV : noms lisibles, adresses complètes, volume cohérent ? Ajuster.

### 3. Validation commerciale — avant toute dépense
L'enrichissement coûte du temps et de l'argent par contact : il ne démarre qu'après accord écrit du client (un email suffit ; acompte si forfait > 200 €). Présenter :
- le nombre d'entreprises trouvées et 10 lignes d'exemple ;
- ce qui suit : recherche email/téléphone, rédaction du message, envoi, rapport ;
- un brouillon de message (email chaleureux de 5–8 lignes valorisant le réseau local ; SMS ≤ 160 caractères) ;
- le devis : périmètre, volume, canaux, délai, mention RGPD, source open data.

### 4. Enrichissement des contacts
Aucun script n'existe encore pour cette étape — à écrire (`enrichir.py`) quand un client a validé :
- **Pappers API** (gratuit limité) : nom du dirigeant des sociétés.
- **Perplexity API** (~0,001–0,01 $/requête) : recherche web email + téléphone + site, requête "nom entreprise + commune".
- Tester sur 10 lignes, vérifier qualité et coût, puis lancer en masse. Écrire le résultat dans un nouveau CSV sans écraser la liste filtrée.

Retour d'expérience (test manuel sur 9 entreprises de Saintes) : 7/9 joignables en moins de 30 s (téléphone public, email direct pour la moitié). Les commerces, professions libérales et artisans avec vitrine sont presque toujours trouvables ; les micro-entrepreneurs sans présence web (consultants solo) ne le sont pas. Estimation réaliste : **50–60 % de la liste enrichissable**, 75–85 % sur les entreprises avec salariés. D'où l'intérêt d'enrichir par vagues : d'abord les entreprises avec salariés, puis les professions libérales (annuaires spécialisés : Doctolib, notaires.fr, Pages Jaunes), en laissant de côté les micro sans activité visible.

### 5. Campagne
- Email : Brevo (gratuit jusqu'à 300/jour, ~20 €/mois au-delà). SMS : Brevo SMS, Octopush, TextingHouse (~0,065 €/SMS).
- Champs dynamiques (nom, commune), test sur 5 contacts, puis envoi par vagues de 50–100/jour pour éviter le spam.

### 6. Rapport
Une page : volume envoyé, taux d'ouverture/clic, réponses, désabonnements, contacts à relancer. Proposer la suite (mise à jour mensuelle, relance, autre périmètre).

## Grille tarifaire indicative

| Prestation | Contenu | Tarif |
|---|---|---|
| Fichier seul | Liste SIRENE filtrée, Excel | 80–150 € |
| Fichier enrichi | + email/téléphone | 200–400 € selon volume |
| Campagne email clé en main | Fichier enrichi + message + envoi + rapport | 350–600 € |
| Campagne email + SMS | + SMS | 450–750 € |
| Forfait mensuel | Mise à jour + campagne | 250–500 €/mois |

Repères marché : fichiers B2B 0,08–0,75 €/contact ; campagne externalisée 300–1 000 € ; prospection clé en main 590–1 690 €/mois. Coûts réels d'une campagne de 500 contacts : enrichissement 1–10 €, email 0–20 €, SMS ~35 €.

## RGPD (points clés)

- Prospection B2B légale sans consentement préalable si le message concerne l'activité professionnelle du destinataire (intérêt légitime).
- Données SIRENE = open data, usage commercial autorisé ; tracer la source.
- Chaque message inclut un moyen de désinscription (lien ou "répondez STOP").
- Le prestataire agit en sous-traitant du client : contrat de prestation ou DPA simple recommandé.
- Sources : [CNIL — vente de fichiers](https://www.cnil.fr/fr/vente-de-fichiers-clients-la-cnil-rappelle-les-regles), [Leto — RGPD et prospection B2B](https://www.leto.legal/guides/rgpd-et-prospection-btob-quelles-regles-respecter).
