# bankstatements

Un schema pour tous les formats de releve bancaire: MT940, MT942, CAMT.053, BAI2, OFX/QFX.

## Quickstart

```bash
pip install bankstatements
bankstatements releve.sta --json
```

```python
from bankstatements import parse

for tx in parse("releve.sta"):
    print(tx.date, tx.amount, tx.counterparty_name)
```

Le meme code lit un MT940 allemand et un QFX de Chase, et rend les memes champs.

## Pourquoi ca existe, et ce que ce n'est pas

Chaque format a sa librairie, et chaque librairie a son schema. Mesure du 2026-08-05: sur la
meme notion de transaction, `mt940` rend 37 champs, `ofxparse` en rend 10, et ils n'ont que
**trois champs en commun** (montant, date, identifiant). La contrepartie s'appelle
`applicant_name` d'un cote et `payee` de l'autre. Quiconque ingere deux formats ecrit son
mapping a la main, puis le reecrit au format suivant.

**Ce n'est pas un nouveau parseur.** Les bons parseurs existent et on s'appuie dessus quand
c'est possible. Ce qui manque est la couche au dessus, plus le corpus en dessous.

**Ce n'est pas de l'extraction par modele.** Un releve bancaire a une grammaire publiee: le
parser avec un modele serait non deterministe, cher au volume et inauditable. Un rapprochement
bancaire ne peut pas etre probabiliste, et un montant faux mais plausible est le pire echec
possible en finance. Le modele a sa place ailleurs, voir plus bas.

**Ce n'est pas un service heberge.** Un releve est le fichier le plus sensible d'une entreprise.
Tout s'execute chez vous, y compris le serveur MCP.

## Le corpus est l'actif, pas le code

Un modele ecrit un parseur conforme a la specification en trente secondes, parce que la
specification est publique. Il ne peut pas savoir que Wells Fargo omet les retours a la ligne
dans l'en-tete d'un QFX, que Chase ecrit des en-tetes tordus, ou qu'une banque emet `cpNONE`
comme encodage. Ce sont des faits sur le monde et non sur la norme.

Les trois exemples sortent d'issues ouvertes et non traitees ailleurs, pas d'une imagination.

`corpus/` est donc versionne comme une donnee neutre: schema JSON, fixtures par banque, regles
de deviation. Les implementations Python et TypeScript le consomment sans qu'aucune ne devienne
la reference. Deux implementations qui portent chacune leur verite divergent.

## Ou le modele sert vraiment

Jamais sur le chemin du parsing. Sur trois points, hors ligne, ou il n'y a pas de specification:

1. Generer une regle de deviation depuis la documentation PDF d'une banque, une fois, puis
   l'executer en deterministe pour toujours.
2. Diagnostiquer un fichier qui ne passe pas et proposer la regle manquante.
3. Lire un releve fourni en PDF, ou il n'y a effectivement aucune grammaire.

## Serveur MCP

Local, en stdio. Le fichier ne quitte pas la machine. Les outils rendent des tranches filtrees
et paginees, jamais le fichier entier: un releve de 5000 transactions detruit une fenetre de
contexte, et c'est la premiere chose qu'une enveloppe naive rate.

## Contribuer

Un rapport qui porte un extrait de fichier anonyme vaut plus qu'une correction de code. Voir
[CONTRIBUTING.md](CONTRIBUTING.md), et le gabarit d'issue "ma banque produit un fichier que la
librairie ne lit pas".

## Licence

MIT.
