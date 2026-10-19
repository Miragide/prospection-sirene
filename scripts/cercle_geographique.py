#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modele reutilisable : calcule tous les codes postaux francais situes dans un
rayon (km) autour d'un code postal centre, via geocodage pgeocode + distance
de haversine. Sert a affiner geographiquement les scripts de filtrage SIRENE
(voir filtrer_sirene.py, zone "rayon") au lieu d'un simple filtre departement.

Sortie :
  - data/communes_dans_rayon.csv  (detail : code postal, commune, departement, distance)
  - liste Python prete a coller dans un script de filtrage (CODES_POSTAUX_CIBLES)

Usage :
  python3 cercle_geographique.py --centre 89400 --rayon 50

Aussi importe par filtrer_sirene.py quand la config utilise une zone "rayon".
"""

import os
import sys
import argparse
import math

try:
    import pgeocode
except ImportError:
    print("Veuillez installer pgeocode : pip install pgeocode", file=sys.stderr)
    sys.exit(1)

import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Distance a vol d'oiseau entre deux points (degres decimaux), en km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def charger_base_codes_postaux(pays: str) -> pd.DataFrame:
    """
    Recupere la base complete des codes postaux geocodes (GeoNames) pour le
    pays. pgeocode ne fournit pas d'API publique pour l'acces en masse : on
    lit son cache interne (._data), telecharge/mis en cache automatiquement
    par pgeocode.Nominatim au premier appel.
    """
    nomi = pgeocode.Nominatim(pays)
    base = nomi._data.copy()
    base = base.dropna(subset=["latitude", "longitude"])
    base["postal_code"] = base["postal_code"].astype(str).str.strip().str.zfill(5)
    # Exclure les codes "CEDEX" (adresses administratives de grandes structures,
    # non utilises comme code postal d'etablissement dans SIRENE)
    base = base[base["postal_code"].str.fullmatch(r"\d{5}")]
    return base


def communes_dans_rayon(cp_centre: str, rayon_km: float, pays: str = "FR") -> pd.DataFrame:
    nomi = pgeocode.Nominatim(pays)
    centre = nomi.query_postal_code(cp_centre)
    if pd.isna(centre.get("latitude")) or pd.isna(centre.get("longitude")):
        raise ValueError(f"Code postal centre introuvable ou non geocode : {cp_centre}")
    lat0, lon0 = float(centre["latitude"]), float(centre["longitude"])

    base = charger_base_codes_postaux(pays)
    base["distance_km"] = base.apply(
        lambda row: haversine_km(lat0, lon0, float(row["latitude"]), float(row["longitude"])),
        axis=1,
    )
    dans_rayon = base[base["distance_km"] <= rayon_km].copy()
    dans_rayon = dans_rayon.sort_values("distance_km")

    resultat = pd.DataFrame({
        "Code postal": dans_rayon["postal_code"],
        "Commune": dans_rayon["place_name"],
        "Département": dans_rayon["postal_code"].str[:2],
        "Distance (km)": dans_rayon["distance_km"].round(1),
    })
    return resultat.drop_duplicates(subset="Code postal")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--centre", required=True, help="Code postal du point central (ex: 89400)")
    ap.add_argument("--rayon", type=float, default=50, help="Rayon en km (defaut: 50)")
    ap.add_argument("--pays", default="FR", help="Code pays ISO2 (defaut: FR)")
    ap.add_argument("--sortie", default="data/communes_dans_rayon.csv", help="Chemin du CSV de sortie")
    args = ap.parse_args()

    print(f"Géocodage du centre ({args.centre}) et calcul des distances…")
    resultat = communes_dans_rayon(args.centre, args.rayon, args.pays)

    os.makedirs(os.path.dirname(args.sortie) or ".", exist_ok=True)
    resultat.to_csv(args.sortie, index=False, encoding="utf-8-sig")

    print(f"\n✓ {len(resultat)} codes postaux trouvés dans un rayon de {args.rayon} km autour de {args.centre}")
    print(f"✓ Détail écrit : {args.sortie}")

    print("\nRépartition par département :")
    for dept, count in resultat["Département"].value_counts().sort_index().items():
        print(f"  {dept:<6} {count:>4}")

    codes = sorted(resultat["Code postal"].tolist())
    print(f"\nListe prete a coller (CODES_POSTAUX_CIBLES) dans un script de filtrage :\n")
    print("CODES_POSTAUX_CIBLES = [")
    for i in range(0, len(codes), 10):
        ligne = ", ".join(f"'{c}'" for c in codes[i:i + 10])
        print(f"    {ligne},")
    print("]")


if __name__ == "__main__":
    main()
