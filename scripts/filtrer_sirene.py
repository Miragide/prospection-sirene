# -*- coding: utf-8 -*-
"""
Filtre la base SIRENE (fichiers Parquet data.gouv.fr) selon une config JSON
et exporte un CSV lisible dans Excel + un rapport de répartition en console.

Usage :
  python filtrer_sirene.py --config ma_campagne.json --data-dir /chemin/vers/parquets

La config décrit la zone, les secteurs (NAF), les effectifs — voir
assets/exemples/*.json et la section "Format de config" de SKILL.md.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).resolve().parent.parent
LIBELLES = json.loads((SKILL_DIR / 'assets' / 'libelles.json').read_text(encoding='utf-8'))
PRESETS = json.loads((SKILL_DIR / 'assets' / 'naf_presets.json').read_text(encoding='utf-8'))

COLONNES_ETAB = [
    'siren', 'siret', 'codeCommuneEtablissement',
    'numeroVoieEtablissement', 'typeVoieEtablissement',
    'libelleVoieEtablissement', 'complementAdresseEtablissement',
    'codePostalEtablissement', 'libelleCommuneEtablissement',
    'activitePrincipaleEtablissement', 'trancheEffectifsEtablissement',
    'dateCreationEtablissement', 'denominationUsuelleEtablissement',
    'enseigne1Etablissement',
]
COLONNES_UL = [
    'siren', 'denominationUniteLegale', 'nomUniteLegale', 'prenom1UniteLegale',
    'categorieJuridiqueUniteLegale', 'activitePrincipaleUniteLegale',
]


def developper_naf(codes):
    """Remplace les références '@preset' par leurs codes NAF."""
    resultat = set()
    for code in codes or []:
        if code.startswith('@'):
            nom = code[1:]
            if nom not in PRESETS:
                sys.exit(f"Preset NAF inconnu : {code} (voir assets/naf_presets.json)")
            resultat |= set(PRESETS[nom])
        else:
            resultat.add(code)
    return resultat


def codes_postaux_rayon(centre, km):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cercle_geographique import communes_dans_rayon
    return communes_dans_rayon(centre, km)['Code postal'].tolist()


def construire_filtre(cfg):
    """Expression PyArrow poussée dans la lecture Parquet (évite de tout charger)."""
    f = (pc.field('etatAdministratifEtablissement') == 'A')
    if cfg.get('sieges_uniquement', True):
        # Le Parquet stocke etablissementSiege en booléen (pas 'O'/'N' comme le CSV)
        f &= pc.field('etablissementSiege') == True  # noqa: E712

    zone = cfg.get('zone', {})
    if 'communes_insee' in zone:
        f &= pc.field('codeCommuneEtablissement').isin(zone['communes_insee'])
    if 'codes_postaux' in zone:
        f &= pc.field('codePostalEtablissement').isin(zone['codes_postaux'])
    if 'departements' in zone:
        dep = pc.utf8_slice_codeunits(pc.field('codeCommuneEtablissement'), 0, 2)
        f &= dep.isin(zone['departements'])
    if 'rayon' in zone:
        cps = codes_postaux_rayon(zone['rayon']['centre'], zone['rayon']['km'])
        print(f"  Rayon {zone['rayon']['km']} km autour de {zone['rayon']['centre']} → {len(cps)} codes postaux")
        f &= pc.field('codePostalEtablissement').isin(cps)
    if not zone:
        sys.exit("La config doit définir une zone (communes_insee, codes_postaux, departements ou rayon).")

    naf_inclus = developper_naf(cfg.get('naf_inclus'))
    if naf_inclus:
        f &= pc.field('activitePrincipaleEtablissement').isin(sorted(naf_inclus))
    if cfg.get('effectifs'):
        f &= pc.field('trancheEffectifsEtablissement').isin(cfg['effectifs'])
    return f


def est_catjur_valide(series):
    """Exclut associations/fondations (9100–9999) et indivisions/fiducies (2100–2199)."""
    cat = pd.to_numeric(series, errors='coerce').fillna(0).astype(int)
    return ~(((cat >= 9100) & (cat <= 9999)) | ((cat >= 2100) & (cat <= 2199)))


def _str(val):
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', '<na>', 'none') else s


def construire_nom(row):
    """Enseigne > raison sociale > Prénom NOM (EI)."""
    for col in ('enseigne1Etablissement', 'denominationUsuelleEtablissement', 'denominationUniteLegale'):
        if _str(row.get(col)):
            return _str(row.get(col))
    return f"{_str(row.get('prenom1UniteLegale'))} {_str(row.get('nomUniteLegale'))}".strip()


def construire_dirigeant(row):
    """Nom du dirigeant : connu seulement pour les personnes physiques (EI / micro)."""
    if _str(row.get('denominationUniteLegale')):
        return ''
    return f"{_str(row.get('prenom1UniteLegale')).title()} {_str(row.get('nomUniteLegale'))}".strip()


def construire_adresse(row):
    voie = ' '.join(p for p in (
        _str(row.get('numeroVoieEtablissement')),
        _str(row.get('typeVoieEtablissement')),
        _str(row.get('libelleVoieEtablissement')),
    ) if p)
    complement = _str(row.get('complementAdresseEtablissement'))
    if complement:
        voie = f"{complement}, {voie}" if voie else complement
    cp, commune = _str(row.get('codePostalEtablissement')), _str(row.get('libelleCommuneEtablissement'))
    if cp and commune:
        voie += f', {cp} {commune}'
    return voie.strip(', ')


def afficher_repartition(titre, serie, total, top=None):
    print(f"\n{titre} :")
    counts = serie.value_counts()
    if top:
        counts = counts.head(top)
    for label, count in counts.items():
        print(f"  {str(label)[:50]:<50} {count:>5}  ({count / total * 100:.0f}%)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True, help='Fichier JSON de config de la campagne')
    ap.add_argument('--data-dir', default='.', help='Dossier contenant les deux fichiers Parquet SIRENE')
    ap.add_argument('--sortie', help='CSV de sortie (prioritaire sur la clé "sortie" de la config)')
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    data_dir = Path(args.data_dir)
    fichier_etab = data_dir / 'StockEtablissement_utf8.parquet'
    fichier_ul = data_dir / 'StockUniteLegale_utf8.parquet'
    for f in (fichier_etab, fichier_ul):
        if not f.exists():
            sys.exit(f"Fichier introuvable : {f} — voir references/sources_donnees.md pour le télécharger.")

    print(f"Campagne : {cfg.get('nom', args.config)}")
    print("Chargement des établissements (filtres poussés dans le Parquet)…")
    etab = ds.dataset(fichier_etab).to_table(columns=COLONNES_ETAB, filter=construire_filtre(cfg)).to_pandas()
    print(f"  → {len(etab)} établissements")
    if etab.empty:
        sys.exit("Aucun établissement ne correspond : vérifier la zone et les filtres.")

    print("Chargement des unités légales (nom, forme juridique, dirigeant)…")
    sirens = etab['siren'].unique().tolist()
    ul = ds.dataset(fichier_ul).to_table(
        columns=COLONNES_UL, filter=pc.field('siren').isin(sirens)).to_pandas()
    merged = etab.merge(ul, on='siren', how='left')

    mask = pd.Series(True, index=merged.index)
    if cfg.get('exclure_non_entreprises', True):
        mask &= est_catjur_valide(merged['categorieJuridiqueUniteLegale'])
    naf_exclus = developper_naf(cfg.get('naf_exclus'))
    if naf_exclus:
        mask &= ~merged['activitePrincipaleEtablissement'].fillna('').isin(naf_exclus)
    df = merged[mask].copy()
    print(f"  → {len(df)} entreprises retenues après exclusions")

    lib_naf, lib_cat, lib_eff = LIBELLES['naf'], LIBELLES['categorie_juridique'], LIBELLES['tranche_effectif']
    df['Nom'] = df.apply(construire_nom, axis=1)
    df['Dirigeant (EI)'] = df.apply(construire_dirigeant, axis=1)
    df['Adresse'] = df.apply(construire_adresse, axis=1)
    df['Code postal'] = df['codePostalEtablissement'].fillna('')
    df['Commune'] = df['libelleCommuneEtablissement'].fillna('').str.title()
    df['Département'] = df['codeCommuneEtablissement'].fillna('').str[:2]
    df['Code NAF'] = df['activitePrincipaleEtablissement'].fillna('')
    df['Activité'] = df['Code NAF'].map(lib_naf).fillna(df['Code NAF'])
    df['Taille'] = df['trancheEffectifsEtablissement'].map(lib_eff).fillna('Non renseigné')
    df['Forme juridique'] = (
        pd.to_numeric(df['categorieJuridiqueUniteLegale'], errors='coerce')
        .astype('Int64').astype(str).map(lib_cat).fillna('Autre forme')
    )
    df['Date création'] = pd.to_datetime(df['dateCreationEtablissement'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
    df['SIRET'] = df['siret'].fillna('')

    colonnes = ['Nom', 'Dirigeant (EI)', 'Forme juridique']
    groupes = cfg.get('groupes_naf')
    if groupes:
        correspondance = {}
        for libelle, codes in groupes.items():
            for code in developper_naf(codes if isinstance(codes, list) else [codes]):
                correspondance.setdefault(code, libelle)
        df['Domaine'] = df['Code NAF'].map(correspondance).fillna('Autre')
        colonnes.append('Domaine')
    colonnes += ['Activité', 'Code NAF', 'Adresse', 'Code postal', 'Commune', 'Département',
                 'Taille', 'Date création', 'SIRET']

    export = df[colonnes].drop_duplicates(subset='SIRET').sort_values(['Commune', 'Nom'])

    sortie = args.sortie or cfg.get('sortie', 'data/sortie_filtree.csv')
    os.makedirs(os.path.dirname(sortie) or '.', exist_ok=True)
    export.to_csv(sortie, index=False, encoding='utf-8-sig')  # utf-8-sig = accents OK dans Excel

    total = len(export)
    print(f"\n✓ Export : {sortie} — {total} entreprises")
    print("\n--- RAPPORT DE LA LISTE ---")
    if groupes:
        afficher_repartition('Répartition par domaine', export['Domaine'], total)
    afficher_repartition('Répartition par taille', export['Taille'], total)
    afficher_repartition('Répartition par forme juridique', export['Forme juridique'], total, top=8)
    afficher_repartition('Top 15 activités', export['Activité'], total, top=15)
    if export['Département'].nunique() > 1:
        afficher_repartition('Répartition par département', export['Département'], total)
    afficher_repartition('Top 15 communes', export['Commune'], total, top=15)


if __name__ == '__main__':
    main()
