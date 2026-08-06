# Banque non nommee: montants ecrits avec la virgule comme separateur decimal

- Banque: non nommee (Bresil)
- Format: OFX 1.0.2 SGML
- Fixture: `montant-virgule-decimale.ofx`
- Sources: jseutter/ofxparse #179 (PR, ouverte le 2024-11-04)
- Provenance: la forme `2000,00` vient des octets de la fixture ajoutee par la PR #179. Tout le reste vient du gabarit commun: le signe negatif du `TRNAMT`, la devise `USD`, les dates de 2026, les identifiants et libelles neutralises. La source, elle, porte `CURDEF` a `BRL` et `LANGUAGE` a `POR`.

## La deviation

Les montants sont ecrits avec une virgule decimale, `2000,00`, et non avec un point. Le fichier place cette forme a la fois dans le `TRNAMT` de la transaction et dans le `BALAMT` du solde comptable, et laisse un autre `BALAMT` en notation a point, ce qui donne un fichier ou les deux notations cohabitent. C est la convention typographique locale, pas une invention de la banque: la specification OFX 1.0.2 decrit le type amount comme acceptant le point ou la virgule comme separateur decimal. Un parseur qui refuse `2000,00`, ou qui le lit comme un separateur de milliers, est donc en tort avant la banque. La difficulte reelle n est pas la conformite, c est l ambiguite: sur une valeur comme `2,000`, la virgule ne dit pas d elle-meme si elle separe les decimales ou les milliers.

Ce que dit la source:

```
<TRNAMT>2000,00
<BALAMT>2000,00
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction, montant `-2000.00` |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction, montant `-2000.00` |
| `ofxtools` 1.1.1 | 1 transaction, `trntype='DEBIT'`, `trnamt=Decimal('-2000.00')` |

Aucun des trois n echoue et aucun ne perd le champ: les trois rendent une transaction dont le montant vaut bien deux mille, la virgule ayant ete traitee comme separateur decimal. Il n y a donc ici ni plantage ni montant ampute en silence, sur ce fichier precis. La mesure ne porte que sur les transactions: elle ne dit rien du `BALAMT` en virgule, dont la lecture n a pas ete verifiee.

## La regle

Normaliser tout champ montant (`TRNAMT`, `BALAMT`, et les autres du type amount) avant conversion, de facon deterministe:

1. Supprimer les espaces, y compris l espace insecable.
2. Si la valeur contient a la fois un point et une virgule, le plus a droite des deux est le separateur decimal; l autre est un separateur de groupes et se supprime.
3. Si la valeur ne contient qu une virgule, une seule fois, suivie de un ou deux chiffres jusqu a la fin: c est le separateur decimal, le remplacer par un point.
4. Si la valeur contient plusieurs virgules: ce sont des separateurs de groupes, les supprimer.
5. Si la valeur ne contient qu une virgule suivie d exactement trois chiffres jusqu a la fin (`2,000`): le cas est ambigu. Signaler la valeur et refuser la conversion, ne pas trancher au hasard.

Une valeur deja conforme comme `-10.00` traverse ces cinq etapes sans etre modifiee.

## Reserve

La banque n est pas nommee; le rattachement au Bresil vient des indices de la fixture d origine (devise, langue), pas d une declaration du rapporteur. Les octets de la fixture sont reconstruits sur le gabarit commun: seule la virgule vient de la source, et la source ecrit `2000,00` en positif la ou la fixture ecrit `-2000,00`.

Surtout, la source ne contredit pas la mesure, elle ne parle simplement pas de ce cas: la PR #179 corrige une ligne vide en tete de fichier, et la virgule n est presente dans sa fixture que par accident, sans que personne ne signale un montant mal lu. Ce cas est donc documente sans defaut reproduit: a la date de la mesure, aucun des trois parseurs ne bute dessus. Sa valeur est preventive, elle tient a l ambiguite du point 5 de la regle, qui n est attestee par aucune mesure ici.
