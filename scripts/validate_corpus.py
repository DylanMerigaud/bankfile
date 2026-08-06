#!/usr/bin/env python3
"""validate_corpus.py: le corpus est l'actif, donc il est valide comme le code.

Il verifie trois choses, et chacune correspond a une facon dont ce genre de depot pourrit:

  une fixture sans son `.md`      un fichier de banque dont personne ne sait ce qu'il illustre
                                  devient du bruit au premier refactor.
  un `.md` sans sa fixture        une deviation racontee mais non reproductible.
  une donnee non anonymisee       le corpus ne porte que du structurel. Un IBAN complet ou un
                                  montant reel est une fuite, meme dans un depot prive: il
                                  deviendra public.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BANKS = Path(__file__).resolve().parent.parent / "corpus" / "banks"
# Un IBAN complet et un numero de carte: les deux formes les plus faciles a oublier dans un
# extrait colle depuis un vrai fichier.
FUITES = (
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)


def main() -> int:
    if not BANKS.is_dir():
        print(f"{BANKS} manque")
        return 1
    fautes: list[str] = []
    fixtures = [p for p in BANKS.rglob("*") if p.is_file() and p.suffix not in (".md",)]
    for f in fixtures:
        if not f.with_suffix(".md").exists():
            fautes.append(f"{f}: aucune note .md, on ne sait pas ce que ce fichier illustre")
        texte = f.read_text(encoding="utf-8", errors="replace")
        for rx in FUITES:
            if rx.search(texte):
                fautes.append(f"{f}: ressemble a une donnee non anonymisee ({rx.pattern[:24]})")
                break
    for note in BANKS.rglob("*.md"):
        if note.name == "README.md":
            continue
        if not any(p.with_suffix(".md") == note for p in fixtures):
            fautes.append(f"{note}: decrit une deviation sans fixture, donc non reproductible")
    for x in fautes:
        print(f"  {x}")
    print(f"{len(fixtures)} fixtures, {len(fautes)} fautes")
    return 1 if fautes else 0


if __name__ == "__main__":
    sys.exit(main())
