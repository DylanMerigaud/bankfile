# LCL: une transaction de type CHECK sans NAME ni MEMO, donc sans beneficiaire

- Banque: LCL (France)
- Format: OFX 1.0.2 SGML
- Fixture: `trntype-check-sans-payee.ofx`
- Sources: jseutter/ofxparse #162 (issue, ouverte le 2020-12-11)
- Provenance: viennent des octets cites dans l issue le `<TRNTYPE>CHECK`, l absence de `<NAME>` et de `<MEMO>` dans le `<STMTTRN>`, et la presence d un `<CHECKNUM>`. Tout le reste (entete, bloc de signon, identifiants de compte, dates, montants, soldes) vient du gabarit commun du corpus, avec des valeurs neutres.

## La deviation

Le releve porte une operation dont le `TRNTYPE` vaut `CHECK` et dont le `STMTTRN` ne contient ni `NAME` ni `MEMO`: le seul libelle disponible est le numero de cheque porte par `CHECKNUM`. Le rapporteur en deduit que ce genre de transaction n est pas traite correctement, parce que le champ payee ressort vide. Le fichier est CONFORME a la specification OFX: `CHECK` est une valeur legitime de `TRNTYPE`, et `NAME` comme `PAYEE` sont optionnels dans un `STMTTRN`. C est le code consommateur qui est en tort quand il suppose qu une transaction porte toujours un beneficiaire, pas la banque. La deviation est donc une deviation d attente, pas de format: elle attaque tout ce qui indexe, categorise ou rapproche par libelle.

Ce que dit la source:

```
<TRNTYPE>CHECK
<DTPOSTED>20190221
<TRNAMT>-19.87
<FITID>003 1090381
<CHECKNUM>1090381
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | succes, 1 transaction, type `check`, montant `-10.00`, date `2026-01-15 00:00:00`, payee `` (vide), memo `` (vide), checknum `T0001` |
| `ofxparse` 0.21, fichier ouvert en binaire | succes, 1 transaction, type `check`, montant `-10.00`, date `2026-01-15 00:00:00`, payee `` (vide), memo `` (vide), checknum `T0001` |
| `ofxtools` 1.1.1 | succes, 1 transaction: `<STMTTRN(trntype='CHECK', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', checknum='T0001')>` |

Aucun des trois parseurs ne leve. Les deux modes de `ofxparse` rendent une transaction complete sur le montant, la date et le numero de cheque, avec `payee` et `memo` a chaine vide; `ofxtools` rend un objet ou ces deux champs sont simplement absents. Le risque n est donc pas un plantage mais un libelle vide qui traverse la chaine sans signal: une operation de dix euros arrive dans un rapprochement sans aucun texte pour l identifier, sauf a lire `checknum`.

## La regle

Ne jamais supposer qu un `STMTTRN` porte un libelle. A l ingestion, construire le libelle par repli ordonne: `NAME`, sinon `PAYEE/NAME`, sinon `MEMO`, sinon, quand `TRNTYPE` vaut `CHECK` et que `CHECKNUM` est renseigne, une valeur derivee du numero de cheque (par exemple `CHECK <checknum>`), sinon une chaine vide explicitement marquee comme absence de libelle plutot que comme libelle vide. Traiter `TRNTYPE` comme une enumeration ouverte de la specification OFX (`CREDIT`, `DEBIT`, `INT`, `DIV`, `FEE`, `SRVCHG`, `DEP`, `ATM`, `POS`, `XFER`, `CHECK`, `PAYMENT`, `CASH`, `DIRECTDEP`, `DIRECTDEBIT`, `REPEATPMT`, `OTHER`) et ne jamais brancher sur les seuls `DEBIT` et `CREDIT`: le signe de `TRNAMT` porte le sens debit/credit, pas `TRNTYPE`. Cette regle ne casse aucun fichier conforme, puisqu elle n ajoute qu un repli la ou le libelle manque.

## Reserve

La mesure contredit la source sur un point important: le rapporteur decrit une transaction qui ne serait pas traitee correctement, et `ofxparse` 0.21 la parse aujourd hui sans erreur dans les deux modes. Soit le comportement a change depuis le rapport de 2020, soit le probleme vecu tenait au code appelant du rapporteur et non au parseur. Ce qui reste etabli et verifie ici, c est la perte silencieuse du libelle, pas un echec de parsing. Les octets de la fixture sont reconstruits: seuls la valeur `CHECK`, l absence de `NAME` et de `MEMO` et la presence de `CHECKNUM` viennent de l issue, les montants, dates et identifiants sont ceux du gabarit. La propriete est attestee par un seul rapporteur, avec une confirmation de lecture de la specification par un second intervenant (fdinel, 2020-12-14) qui conclut que `CHECK` est valide et `PAYEE` optionnel.
