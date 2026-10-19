# prospection-sirene

Skill pour agent IA (Claude Code, Claude.ai…) qui construit des listes de prospection B2B françaises à partir de la base SIRENE (open data data.gouv.fr).

## Installation

1. Copier ce dossier dans `~/.claude/skills/prospection-sirene/` (Claude Code) — ou installer le fichier `prospection-sirene.skill` depuis Claude.ai.
2. `pip install -r requirements.txt`
3. Télécharger les deux fichiers Parquet SIRENE (`StockEtablissement_utf8.parquet`, `StockUniteLegale_utf8.parquet`) — liens dans `references/sources_donnees.md`. Ils ne sont pas inclus (~3 Go).

Ensuite, il suffit de demander à l'agent, par exemple : « liste-moi les boulangers et traiteurs actifs dans un rayon de 30 km autour de Niort ».

## Contenu

- `SKILL.md` — instructions lues par l'agent
- `scripts/filtrer_sirene.py` — filtrage SIRENE piloté par une config JSON
- `scripts/cercle_geographique.py` — codes postaux dans un rayon autour d'un point
- `scripts/prioriser.py` — réduit une liste par taille / ancienneté
- `assets/` — groupes de codes NAF, libellés, exemples de configs de campagnes réelles
- `references/` — sources de données, workflow commercial, tarifs, RGPD

Utilisable aussi sans agent : `python scripts/filtrer_sirene.py --config assets/exemples/saintes_club_entrepreneurs.json --data-dir /chemin/parquets`
