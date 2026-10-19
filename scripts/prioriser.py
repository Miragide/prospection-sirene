# -*- coding: utf-8 -*-
"""
Réduit un CSV produit par filtrer_sirene.py aux profils prioritaires, selon la
taille et l'ancienneté de l'établissement. Utile quand la liste brute est trop
longue pour être enrichie (l'enrichissement coûte par contact).

Exemple (cible d'une assistante administrative : très petites structures récentes) :
  python prioriser.py data/liste.csv data/liste_prioritaire.csv \
      --tailles "Non renseigné" "0 salarié" "1–2 salariés" --anciennete-max 5

Les entreprises sans date de création exploitable sont exclues dès qu'un
critère d'ancienneté est donné (impossible de vérifier le critère).
"""

import argparse
import os
import sys

import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('entree')
    ap.add_argument('sortie')
    ap.add_argument('--tailles', nargs='+', help='Libellés de la colonne "Taille" à garder')
    ap.add_argument('--anciennete-max', type=float, help='Ancienneté maximale en années')
    ap.add_argument('--anciennete-min', type=float, help='Ancienneté minimale en années')
    args = ap.parse_args()

    df = pd.read_csv(args.entree, dtype=str, encoding='utf-8-sig')
    print(f"{len(df)} entreprises chargées depuis {args.entree}")

    date = pd.to_datetime(df['Date création'], format='%d/%m/%Y', errors='coerce')
    df['Ancienneté (années)'] = ((pd.Timestamp.now() - date).dt.days / 365.25).round(1)

    mask = pd.Series(True, index=df.index)
    if args.tailles:
        inconnues = set(args.tailles) - set(df['Taille'].unique())
        if inconnues:
            print(f"  ⚠ Tailles absentes du fichier : {sorted(inconnues)} — valeurs présentes : {sorted(df['Taille'].unique())}")
        mask &= df['Taille'].isin(args.tailles)
    if args.anciennete_max is not None or args.anciennete_min is not None:
        print(f"  ({date.isna().sum()} entreprises sans date de création — exclues)")
        if args.anciennete_max is not None:
            mask &= df['Ancienneté (années)'] <= args.anciennete_max
        if args.anciennete_min is not None:
            mask &= df['Ancienneté (années)'] >= args.anciennete_min

    export = df[mask].sort_values('Ancienneté (années)')
    os.makedirs(os.path.dirname(args.sortie) or '.', exist_ok=True)
    export.to_csv(args.sortie, index=False, encoding='utf-8-sig')

    total = len(export)
    print(f"\n✓ Export : {args.sortie} — {total} entreprises ({total / max(len(df), 1) * 100:.0f}% de la liste)")
    for col, top in (('Domaine', None), ('Taille', None), ('Activité', 15), ('Commune', 15)):
        if col in export.columns and total:
            print(f"\nRépartition par {col.lower()} :")
            counts = export[col].value_counts()
            for label, count in (counts.head(top) if top else counts).items():
                print(f"  {str(label)[:50]:<50} {count:>5}  ({count / total * 100:.0f}%)")


if __name__ == '__main__':
    main()
