# HSBC Brasil: un DTSTART sur six chiffres au format JJMMAA au lieu de AAAAMMJJ

- Banque: HSBC Brasil (Bresil)
- Format: OFX 1.0.2 SGML
- Fixture: `dtstart-format-ddmmyy.ofx`
- Sources: jseutter/ofxparse #58 (issue, ouverte le 2013-10-10)
- Provenance: la deviation vient des octets decrits dans l issue (le champ `DTSTART` du `BANKTRANLIST` ecrit en `%d%m%y`). Tout le reste du fichier vient du gabarit commun du corpus: en-tete, signon, compte anonyme, une transaction unique, soldes. L issue ne publie pas le fichier d origine, seule la forme du champ est attestee.

## La deviation

Le seul octet qui separe cette fixture du gabarit commun est la valeur de `DTSTART`: `010126` au lieu de `20260101`. La specification OFX 1.0.2 impose pour un champ date le format `AAAAMMJJ` eventuellement suivi de l heure, donc une valeur d au moins huit chiffres. Six chiffres ne sont conformes a rien, et la banque est ici clairement en tort: aucun parseur n a a deviner ce decoupage. Pire, `010126` est ambigu meme en connaissant sa longueur, puisqu il se lit `01/01/26` en JJMMAA (la lecture que donne le rapporteur) mais `2001-01-26` en AAMMJJ. Le champ touche est une borne de periode du releve, pas une date de transaction: le risque porte sur la fenetre affichee, pas directement sur un montant.

Ce que dit la source:

```
The HSBC Brasil ofx file parse fail because BANKTRANLIST :: DTSTART tag is in %d%m%y format.

The error happens on ofxparse.py line 396.
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | succes, 1 transaction, debit -10.00 du 2026-01-15, payee `ANON MERCHANT` |
| `ofxparse` 0.21, fichier ouvert en binaire | succes, 1 transaction, debit -10.00 du 2026-01-15, payee `ANON MERCHANT` |
| `ofxtools` 1.1.1 | echec: `OFXSpecError: Can't set BANKTRANLIST.dtstart to 010126: '010126' does not conform to OFX formats for <class 'datetime.datetime'>` |

`ofxtools` refuse le fichier entier et nomme le champ fautif, ce qui est le comportement le plus lisible des trois. `ofxparse` 0.21 ne leve rien dans les deux modes et rend la transaction complete et exacte, montant et date de comptabilisation compris: la valeur douteuse est donc confinee a la borne de periode, sans contaminer les ecritures. La mesure ne releve pas la valeur que `ofxparse` attribue a `DTSTART`, donc on ne sait pas si elle est corrigee, mal interpretee ou abandonnee, et cette note n en affirme rien.

## La regle

Sur `DTSTART` et `DTEND`, tenter d abord `AAAAMMJJ` sur les huit premiers caracteres, comportement inchange pour un fichier conforme. Si et seulement si la valeur nettoyee fait exactement six chiffres, ne pas deviner: ne jamais choisir silencieusement entre JJMMAA et AAMMJJ. Laisser la borne de periode a nul, marquer le releve d un signalement nomme (champ, valeur brute, deux lectures possibles avec leurs dates), et continuer a parser les transactions, dont les propres dates sont sur huit chiffres et restent fiables. Une resolution en JJMMAA n est admissible que si l appelant a declare explicitement cette convention pour l emetteur, jamais par defaut. Un echec dur sur ce seul champ est disproportionne: il jette un releve dont toutes les ecritures sont saines.

## Reserve

Les octets sont reconstruits, pas d origine: l issue #58 decrit le format du champ mais ne joint aucun extrait de fichier, donc `010126` est notre propre valeur, choisie coherente avec le `20260101` du gabarit. La deviation est attestee par une seule personne, en 2013, sur des fichiers HSBC Brasil de cette epoque, et rien ne dit qu elle vaut encore aujourd hui. Point important: la mesure contredit la source. Le rapporteur decrit un plantage de `ofxparse` sur ce format, et `ofxparse` 0.21 ne plante pas sur cette fixture, dans aucun des deux modes. Soit le code a change depuis 2013 (l issue vise une ligne 396 qui n a plus de raison d etre la meme), soit le fichier reel portait d autres particularites que nos octets reconstruits ne reproduisent pas. La lecture JJMMAA elle-meme n est pas verifiee: elle vient du correctif propose par le rapporteur, pas d une comparaison avec un releve papier.
