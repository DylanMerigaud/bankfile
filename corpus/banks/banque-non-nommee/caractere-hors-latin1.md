# Banque non nommee: un nom de beneficiaire porte un caractere hors latin-1

- Banque: non nommee (Slovenie)
- Format: OFX 1.0.2 SGML
- Fixture: `caractere-hors-latin1.ofx` (utf-8)
- Sources: jseutter/ofxparse #169 (issue, ouverte le 2022-05-31)
- Provenance: l entete `ENCODING:UTF-8` / `CHARSET:NONE` et la presence d un caractere hors latin-1 dans `<NAME>` viennent des octets cites dans l issue. Tout le reste (etablissement, identifiants, dates, montants, structure) vient du gabarit commun du corpus; le libelle a ete anonymise en `ANON UPRAVA č` en ne conservant que le caractere qui porte la deviation, le U+010D (c hacek), encode en utf-8 sur deux octets, `C4 8D`.

## La deviation

Le fichier annonce dans son entete `ENCODING:UTF-8` avec `CHARSET:NONE`, et le corps contient effectivement un caractere multi-octets en utf-8 dans le libelle d une transaction. Le gabarit du corpus, lui, annonce `ENCODING:USASCII` / `CHARSET:1252` et reste en ASCII pur. Rien ici ne viole la structure OFX: les balises, l ordre des elements et le format des montants et des dates sont intacts, la seule chose qui sort de l ordinaire est un octet superieur a 0x7F dans une valeur textuelle, annonce par l entete. Le tort etait du cote du parseur, qui reencodait le texte lu en latin-1 sans regarder l entete, ce qui exclut par construction tout caractere hors du plan 0 a 255.

Ce que dit la source:

```
ENCODING:UTF-8
CHARSET:NONE
```

```
<NAME>Finančna uprava RS</NAME>
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | echec: `UnicodeEncodeError: 'latin-1' codec can't encode character 'č' in position 625: ordinal not in range(256)` |
| `ofxparse` 0.21, fichier ouvert en binaire | succes, 1 transaction, `payee` = `ANON UPRAVA č`, montant `-10.00` |
| `ofxtools` 1.1.1 | succes, 1 transaction, `name='ANON UPRAVA č'`, `trnamt=Decimal('-10.00')` |

L usage documente d ofxparse, ouvrir le fichier en mode texte, est le seul des trois a echouer, et il echoue bruyamment: aucun risque de montant errone qui passe. En mode binaire, ofxparse 0.21 rend le libelle complet avec son caractere intact, et ofxtools 1.1.1 fait de meme. Aucun champ n est perdu en silence dans cette fixture, aucun caractere n est remplace par un substitut.

## La regle

Ouvrir le fichier en binaire, toujours, et ne jamais reencoder le contenu vers latin-1 ou ASCII. Choisir le codec en lisant l entete OFX 1.x: `ENCODING:UTF-8` (extension de fait, hors des valeurs `USASCII` et `UNICODE` du format d origine) se decode en utf-8; `ENCODING:USASCII` avec un `CHARSET` numerique se decode dans la page de code correspondante (`CHARSET:1252` en cp1252, `CHARSET:8859-1` en latin-1); `CHARSET:NONE` ne contredit pas l encodage declare et ne doit pas provoquer de repli sur ASCII. En dernier recours, si l entete est absent ou ment, tenter utf-8 puis cp1252, et ne jamais decoder avec `errors='ignore'`, qui amputerait un libelle sans le signaler. Un fichier entierement ASCII passe inchange par cette regle, quel que soit le chemin choisi.

## Reserve

La banque n est pas nommee dans l issue; le pays, la Slovenie, est deduit du libelle cite (`Finančna uprava RS`, l administration fiscale slovene) et du numero de compte slovene present dans la source, non cite ici. Les octets de la fixture sont reconstruits sur le gabarit commun, pas les octets originaux du rapporteur.

Point important: la mesure contredit la source. Le rapporteur ecrit en 2022 que le fichier ne peut etre lu ni en mode texte ni en mode binaire, et joint pour le mode binaire un `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc4`. Avec ofxparse 0.21 en 2026, le mode binaire passe et rend le libelle correct. Seul l echec en mode texte se reproduit. La deviation reste donc reelle et documentee, mais son impact s est reduit a un seul chemin d appel; la version d ofxparse du rapporteur n est pas indiquee dans l issue, et la difference peut venir de la version comme de la reconstruction de la fixture.
