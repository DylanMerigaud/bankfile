# Wells Fargo: tout l entete OFX tient sur une seule ligne, sans aucun retour ligne

- Banque: Wells Fargo (Etats-Unis)
- Format: OFX 1.0.2 SGML (extension QFX)
- Fixture: `entete-sans-retour-ligne.qfx`
- Sources: jseutter/ofxparse #172 (PR, ouverte le 2023-08-04)
- Provenance: la ligne d entete est reproduite octet pour octet depuis le corps de la PR. Tout le reste du fichier (corps `<OFX>`, releve, transaction, soldes) vient du gabarit commun du corpus et n a rien de Wells Fargo.

## La deviation

Les neuf paires cle:valeur de l entete OFX sont concatenees sur une seule ligne, sans separateur entre elles: `OFXHEADER:100` est immediatement suivi de `DATA:OFXSGML`, et ainsi de suite jusqu a `NEWFILEUID:NONE`. Seule la ligne vide qui precede `<OFX>` subsiste. La specification OFX 1.0.2 decrit l entete comme une suite de lignes `cle:valeur`, une par ligne, terminee par une ligne vide: ici c est bien le fichier de la banque qui est hors specification, pas le parseur qui serait trop strict. La consequence pratique est qu un parseur qui coupe l entete sur les retours ligne obtient une ligne unique contenant neuf deux-points, et casse sur le decoupage en cle et valeur.

Ce que dit la source:

```
OFXHEADER:100DATA:OFXSGMLVERSION:102SECURITY:NONEENCODING:USASCIICHARSET:1252COMPRESSION:NONEOLDFILEUID:NONENEWFILEUID:NONE
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | `ValueError: too many values to unpack (expected 2)` |
| `ofxparse` 0.21, fichier ouvert en binaire | `ValueError: too many values to unpack (expected 2)` |
| `ofxtools` 1.1.1 | succes, 1 transaction, `<STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT', memo='ANON` |

`ofxparse` echoue de la meme facon dans les deux modes d ouverture, et il echoue bruyamment: l exception tombe avant toute lecture des transactions, donc aucun montant errone ne sort. `ofxtools` accepte le fichier et rend la transaction complete. Le desaccord porte donc sur la tolerance a l entete, pas sur le contenu du releve.

## La regle

Isoler le bloc d entete: les octets qui precedent le premier `<` du fichier. Compter les `:` et les retours ligne dans ce bloc. Si le nombre de `:` depasse le nombre de retours ligne de plus d un, l entete est collapse: reinserer un retour ligne devant la premiere occurrence de chacune des cles connues (`DATA`, `VERSION`, `SECURITY`, `ENCODING`, `CHARSET`, `COMPRESSION`, `OLDFILEUID`, `NEWFILEUID`), puis reduire les retours ligne consecutifs a un seul. Un entete deja conforme ne remplit pas la condition de comptage et traverse le traitement inchange. Apres decoupage, valider chaque valeur contre son domaine attendu (`OFXHEADER` numerique, `DATA` egal a `OFXSGML`, `VERSION` numerique, etc.): une cle non prevue par la liste resterait collee a la valeur precedente, et il faut echouer explicitement sur cette valeur invalide plutot que la laisser passer.

## Reserve

Seul l entete est atteste par la source; le corps du releve est synthetique et ne prouve rien sur le format reel de Wells Fargo au dela de l entete. La banque n est nommee que par le titre et le commentaire de la PR, par un seul rapporteur, en 2023, et le comportement actuel de l exportateur Wells Fargo n a pas ete reverifie. La mesure confirme le plantage decrit par la source, sans contradiction: le rapporteur annonce `ValueError: too many values to unpack`, et c est exactement ce que rend `ofxparse` 0.21 aujourd hui.
