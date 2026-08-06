#!/usr/bin/env python3
"""validate_corpus.py: le corpus est l'actif, donc il est valide comme le code.

Il verifie cinq choses, et chacune correspond a une facon dont ce genre de depot pourrit:

  une fixture sans son `.md`      un fichier de banque dont personne ne sait ce qu'il illustre
                                  devient du bruit au premier refactor.
  un `.md` sans sa fixture        une deviation racontee mais non reproductible.
  une donnee non anonymisee       le corpus ne porte que du structurel. Un IBAN complet ou un
                                  montant reel est une fuite, meme dans un depot prive: il
                                  deviendra public.
  une note sans ses quatre faits  banque, format, fixture, source. Sans la source surtout: une
                                  deviation qu'on ne peut plus remonter n'est plus verifiable,
                                  c'est une affirmation.
  une note qui cite un compte     les notes citent des issues publiques, et une issue publique
                                  contient parfois un vrai numero de compte. Le fichier est
                                  anonymise, la note doit l'etre autant.
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
# Les quatre faits sans lesquels une note ne sert a rien. Ils sont la forme ecrite de la seule
# question qui compte devant une fixture: d'ou sort-elle, et qui peut le verifier.
FAITS = ("- Banque:", "- Format:", "- Fixture:", "- Sources:")


def fuites(chemin: Path) -> list[str]:
    texte = chemin.read_text(encoding="utf-8", errors="replace")
    trouve = []
    for rx in FUITES:
        m = rx.search(texte)
        if m:
            trouve.append(f"{chemin}: ressemble a une donnee non anonymisee ({m.group(0)!r})")
    return trouve


def main() -> int:
    if not BANKS.is_dir():
        print(f"{BANKS} manque")
        return 1
    fautes: list[str] = []
    fixtures = [p for p in BANKS.rglob("*") if p.is_file() and p.suffix not in (".md",)]
    for f in fixtures:
        note = f.with_suffix(".md")
        if not note.exists():
            fautes.append(f"{f}: aucune note .md, on ne sait pas ce que ce fichier illustre")
            continue
        fautes += fuites(f)
        texte = note.read_text(encoding="utf-8", errors="replace")
        manquants = [fait for fait in FAITS if fait not in texte]
        if manquants:
            fautes.append(f"{note}: la note ne dit pas {' ni '.join(manquants)}")
        elif f.name not in texte:
            # Une note qui nomme une autre fixture que sa voisine a ete copiee sans etre relue,
            # et elle decrit alors le mauvais fichier en silence.
            fautes.append(f"{note}: ne nomme pas sa propre fixture {f.name}")
    for note in BANKS.rglob("*.md"):
        if note.name == "README.md":
            continue
        if not any(p.with_suffix(".md") == note for p in fixtures):
            fautes.append(f"{note}: decrit une deviation sans fixture, donc non reproductible")
            continue
        fautes += fuites(note)
    for x in fautes:
        print(f"  {x}")
    print(f"{len(fixtures)} fixtures, {len(fautes)} fautes")
    return 1 if fautes else 0


if __name__ == "__main__":
    sys.exit(main())
