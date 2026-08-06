# Banque non nommee: le numero de cheque est porte par `CHKNUM` au lieu de `CHECKNUM`

- Banque: non nommee
- Format: OFX 1.0.2 SGML
- Fixture: `chknum-au-lieu-de-checknum.ofx`
- Sources: jseutter/ofxparse #173 (PR, ouverte le 2023-11-27)
- Provenance: la seule ligne qui vient de la source est `<CHKNUM>1932`, prise dans le cas de test ajoute par la PR. Tout le reste (montant -10.00, date 20260115, `FITID`, libelles, soldes, en-tete) vient du gabarit commun du corpus. La source portait autour de cette ligne un montant -113.71, une date 20231121 et un `FITID` 0000489: ces valeurs ne sont pas la deviation et ne sont pas reprises.

## La deviation

Dans un `STMTTRN`, la specification OFX nomme le champ du numero de cheque `CHECKNUM`. Ce fichier ecrit `CHKNUM`, forme abregee qui n existe nulle part dans la specification. Le fichier n est donc pas conforme et c est l emetteur qui est en tort, pas le parseur: un parseur qui ignore `CHKNUM` applique la specification a la lettre. La consequence est quand meme grave, parce que le tag inconnu ne casse rien: il traverse un parseur SGML tolerant sans lever, et la transaction ressort simplement sans son numero de cheque. L auteur de la PR le formule ainsi: "It's the same than `checknum`, I don't know why there are two names for the same thing."

Ce que dit la source:

```
    <CHKNUM>1932
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO`, `checknum` vide |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO`, `checknum` vide |
| `ofxtools` 1.1.1 | 1 transaction lue, `STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT', memo='ANON` (repr tronque dans la mesure) |

Aucun des trois parseurs n echoue, et c est precisement le probleme: le numero de cheque 1932 est perdu en silence. ofxparse 0.21 rend une transaction dont l attribut `checknum` est la chaine vide, sans avertissement, donc rien dans l objet ne signale qu une information du fichier a ete jetee. La mesure ofxtools montre une transaction lue sans erreur; le repr enregistre est tronque avant la fin, elle n etablit donc ni la presence ni l absence d un champ `checknum` cote ofxtools.

## La regle

A la lecture d un `STMTTRN`, chercher `CHECKNUM`; si le tag est absent, chercher `CHKNUM` et alimenter le meme champ avec sa valeur, en conservant la chaine telle quelle (les zeros de tete d un numero de cheque sont significatifs). Si les deux tags sont presents, garder `CHECKNUM` et signaler le doublon plutot que d en choisir un au hasard. A l ecriture, ne jamais produire `CHKNUM`: la sortie porte toujours `CHECKNUM`. Un fichier conforme n a pas de `CHKNUM`, la branche de repli ne s active donc jamais sur lui.

## Reserve

Plusieurs points ne sont pas etablis. La banque n est pas nommee et le pays est inconnu: la PR ne dit pas quel emetteur produit `CHKNUM`, et la propriete n est attestee que par une personne, en novembre 2023. Les octets de la source ne sont pas un releve reel non plus, mais un extrait de test ecrit a la main dans la PR, ce qui laisse ouverte la question de la forme exacte du fichier d origine. Enfin la mesure contredit ce que la source laisse attendre: la PR ajoute le support de `chknum` et fait passer `__version__` a 0.21, or ofxparse 0.21 tel que publie ne lit pas ce tag et rend `checknum` vide. Le correctif decrit dans la source n est pas dans la version distribuee que nous mesurons.
