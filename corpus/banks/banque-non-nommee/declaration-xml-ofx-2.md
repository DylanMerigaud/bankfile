# Banque non nommee: un OFX 2.x qui declare son encodage dans la declaration XML, la ou ofxparse ne regarde pas

- Banque: non nommee
- Format: OFX 2.x XML (VERSION="202", OFXHEADER="200")
- Fixture: `declaration-xml-ofx-2.ofx` (UTF-8)
- Sources: jseutter/ofxparse #133 (issue, ouverte le 2017-11-28)
- Provenance: les deux lignes de tete (declaration XML et instruction de traitement OFX) viennent des octets cites dans l issue; tout le reste (arborescence, montants, dates, libelles) vient du gabarit commun du corpus, transpose en XML, avec un libelle accentue pour porter la deviation.

## La deviation

Le fichier est un OFX 2.x: il ouvre sur la declaration XML standard, qui porte l attribut `encoding="UTF-8"`, puis sur l instruction de traitement `<?OFX ...?>`. Il n y a donc aucun bloc d entetes SGML `cle:valeur`, et en particulier aucune ligne `ENCODING:` ni `CHARSET:`: la specification OFX 2.2 (section 2.2) les a retirees, l instruction `<?OFX?>` ne porte plus que OFXHEADER, VERSION, SECURITY, OLDFILEUID et NEWFILEUID. Le fichier est donc CONFORME a la specification, et c est le parseur qui est en tort: ofxparse cherche l encodage dans les entetes SGML, n en trouve aucun, et retombe sur ASCII. Tant que le document ne contient que de l ASCII la faute reste invisible, ce que confirme le rapporteur en notant que les fixtures OFX 2.x du projet passent parce qu elles n ont aucun caractere accentue. Des qu un libelle porte un octet non ASCII, la lecture casse.

Ce que dit la source:

```
<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | echec: `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc9 in position 942: ordinal not in range(128)` |
| `ofxparse` 0.21, fichier ouvert en binaire | echec: `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 942: ordinal not in range(128)` |
| `ofxtools` 1.1.1 | succes: 1 transaction, `<STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON ÉNERGIE', memo='ANON ` |

ofxparse echoue dans les deux modes d ouverture, et l echec est bruyant: l exception tombe avant toute transaction, rien n est rendu, donc aucun montant faux n entre dans un rapprochement. La seule difference entre les deux modes est l octet signale (0xc9 en mode texte, 0xc3 en binaire, meme position 942), signe que la donnee est deja passee par un decodage different avant de heurter le meme repli ASCII. ofxtools lit le fichier sans se plaindre et rend le libelle accentue intact.

## La regle

A l ouverture, decider de l encodage avant de choisir le parseur. Si les premiers octets utiles du fichier sont `<?xml`, ne pas chercher d entetes SGML: lire l attribut `encoding` de la declaration XML et decoder avec celui-la; si l attribut est absent, appliquer la regle XML 1.0 (UTF-8 par defaut, apres examen de la marque d ordre des octets). Ne jamais retomber sur ASCII pour un document OFX 2.x: l absence de bloc `cle:valeur` y est normale et ne doit pas etre traitee comme un entete manquant. Pour un fichier OFX 1.x (premiers octets `OFXHEADER:`), conserver la lecture des entetes `ENCODING:`/`CHARSET:` inchangee, de sorte qu un fichier conforme a l une ou l autre version reste lu comme avant.

## Reserve

La banque n est pas nommee et le pays n est pas atteste: l issue reunit plusieurs rapporteurs (2017, 2021, 2023, 2025, 2026) sur le meme defaut, sans qu on puisse rattacher ces deux lignes de tete a un etablissement precis. Les octets cites sont authentiques, mais le corps du fichier est reconstruit a partir du gabarit du corpus: la position 942 signalee par les mesures est donc celle de notre fixture, pas celle d un releve reel. Le libelle accentue est aussi de notre fait; le rapporteur de 2021 decrivait `<NAME>Direction Générale des Finances </NAME>` et l erreur `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe9`, octet different parce que le caractere differe. La mesure ne contredit pas la source: le meme type d exception, sur le meme repli ASCII, se reproduit ici. A noter que l issue est ouverte depuis 2017 et qu un correctif prototype circule depuis 2021 sans avoir ete integre; la version 0.21 mesuree porte toujours le defaut.
