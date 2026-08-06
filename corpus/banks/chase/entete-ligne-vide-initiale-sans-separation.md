# Chase: une ligne vide avant l entete, et aucune ligne vide entre l entete et le SGML

- Banque: Chase (Etats-Unis)
- Format: QFX (OFX 1.0.2 SGML)
- Fixture: `entete-ligne-vide-initiale-sans-separation.qfx` (cp1252)
- Sources: jseutter/ofxparse #160 (PR, ouverte le 2020-09-29)
- Provenance: la forme de l entete (ligne vide initiale, `<OFX>` colle a `NEWFILEUID:NONE`) et l octet non-ASCII dans le libelle de transaction viennent des octets cites dans la PR; le corps du releve (montants, dates, identifiants, structure BANKMSGSRSV1) vient du gabarit commun du corpus et ne reproduit pas le fichier d origine.

## La deviation

Le fichier commence par une ligne vide, avant meme `OFXHEADER:100`, et ne place aucune ligne vide entre le dernier en-tete `NEWFILEUID:NONE` et l ouverture `<OFX>`. La specification OFX 1.0.2 decrit un bloc d en-tete de la forme cle deux-points valeur, termine par une ligne vide qui le separe des donnees SGML: sur ces deux points le fichier de Chase s ecarte de la specification, la banque est bien en tort ici, et non le parseur. Un lecteur d en-tete naif casse dans les deux sens: il s arrete a la premiere ligne vide et ne lit donc aucun en-tete, ou bien il tente de decouper `<OFX>` sur un deux-points qui n existe pas. Le fichier porte en plus une contradiction interne d encodage, `ENCODING:USASCII` avec `CHARSET:1252`, alors que le libelle de la transaction contient l octet 0xa6, hors ASCII.

Ce que dit la source:

```

OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
<OFX>
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa6 in position 620: invalid start byte` |
| `ofxparse` 0.21, fichier ouvert en binaire | `UnicodeDecodeError: 'ascii' codec can't decode byte 0xa6 in position 620: ordinal not in range(128)` |
| `ofxtools` 1.1.1 | 1 transaction, `<STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON ¦ MERCHANT', memo='AN` |

Les deux passes `ofxparse` echouent bruyamment, et sur le meme octet: la position 620 tombe dans le libelle de la transaction, loin derriere le bloc d en-tete. `ofxtools` 1.1.1 rend la transaction complete, montant `-10.00` et libelle avec son octet 0xa6 decode en `¦`. Aucun des trois parseurs ne rend ici de transaction amputee en silence: le seul risque mesure est l arret, pas le chiffre faux.

## La regle

Avant tout decoupage de l en-tete, sauter les lignes vides en tete de fichier au lieu de les traiter comme fin de bloc. Ensuite, lire ligne a ligne et terminer le bloc d en-tete a la premiere de ces trois conditions: une ligne qui ne contient pas de deux-points, une ligne qui commence par `<`, ou la fin des donnees lues. Ne jamais exiger la ligne vide de separation, et ne jamais consommer la ligne qui ouvre le SGML. Un fichier conforme, dont l en-tete est suivi d une ligne vide puis de `<OFX>`, passe cette regle a l identique: la ligne vide est sautee, `<OFX>` termine le bloc. Pour le decodage, ne pas faire confiance a `ENCODING:USASCII` quand `CHARSET:1252` est present: ouvrir en binaire et decoder selon `CHARSET`, avec repli tolerant plutot qu exception, sinon un seul octet accentue coute tout le releve.

## Reserve

Ce qui est atteste par la source, ce sont exactement les onze lignes d en-tete citees ci-dessus et le libelle non-ASCII; le reste du fichier de corpus est reconstruit sur le gabarit commun et ne doit pas etre lu comme des octets Chase. La mesure contredit le recit de la source sur le point qui compte: la PR de 2020 decrit un echec de lecture de l en-tete, et en 2026 `ofxparse` 0.21 ne meurt plus sur l en-tete mais sur l encodage, a un octet situe bien apres le bloc d en-tete. Autrement dit le correctif d en-tete propose en #160 semble avoir ete absorbe, tandis que la seconde moitie du cas, l octet cp1252 dans un fichier declare USASCII, reste non traitee. La deviation d en-tete elle-meme n est donc plus verifiee en execution sur cette fixture: elle est attestee par le rapport et par les octets cites, pas par un echec observe le 2026-08-05. Le comportement est rapporte par une seule personne (fyhuang) sur un export du site Chase de 2020; rien n etablit qu il vaut encore pour les exports actuels.
