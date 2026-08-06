# E*Trade: l en-tete declare `CHARSET:NONE` avec `ENCODING:USASCII`

- Banque: E*Trade (Etats-Unis)
- Format: OFX 1.0.2 SGML
- Fixture: `charset-none-avec-encoding-usascii.ofx`
- Sources: jseutter/ofxparse #171 (issue, ouverte le 2023-02-26), jseutter/ofxparse #154 (issue, ouverte le 2019-11-15), jseutter/ofxparse #163 (PR, ouverte le 2021-02-07)
- Provenance: les deux lignes d en-tete `ENCODING:USASCII` et `CHARSET:NONE` viennent des octets cites dans #171 (et redits a l identique dans #154 et #163). Tout le reste du fichier vient du gabarit commun du corpus, ou seule la valeur de `CHARSET` a ete changee: le gabarit porte `CHARSET:1252`.

## La deviation

Le fichier annonce `ENCODING:USASCII` puis `CHARSET:NONE` dans l en-tete OFX 1.x. Le corps est de l ASCII pur, donc le couple est coherent avec lui-meme: il n y a aucun octet hors ASCII a decoder. La deviation n est pas dans les donnees, elle est dans la valeur litterale `NONE`, que `ofxparse` concatene mecaniquement en `cp` + valeur pour fabriquer un nom de codec Python. Le resultat, `cpNONE`, n existe pas. Le fichier ne casse pas la structure SGML et ne perd aucun champ: c est le parseur qui fabrique un nom de codec a partir d une valeur qu il n a pas prevue, et qui echoue avant meme d avoir lu une transaction.

Ce que dit la source:

```
ENCODING:USASCII
CHARSET:NONE
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | `LookupError: unknown encoding: cpNONE` |
| `ofxparse` 0.21, fichier ouvert en binaire | `LookupError: unknown encoding: cpNONE` |
| `ofxtools` 1.1.1 | succes, 1 transaction (`trntype='DEBIT'`, `trnamt=Decimal('-10.00')`, `fitid='T0001'`) |

`ofxparse` echoue de facon identique dans les deux modes d ouverture, et il echoue tot: l exception part de la lecture de l en-tete, donc rien n est parse du tout. `ofxtools` 1.1.1 lit le fichier sans broncher et rend la transaction complete. Aucun des deux ne perd un champ en silence: ici le mode de defaillance est franc, le fichier passe ou il plante.

## La regle

Au moment de resoudre l encodage depuis l en-tete OFX 1.x, ne jamais construire un nom de codec par concatenation aveugle. Traiter `CHARSET` par table:

- `NONE` : decoder en ASCII, ou en `cp1252` si l on veut tolerer des octets hauts non declares (`cp1252` est un sur-ensemble de l ASCII, donc un fichier reellement ASCII est lu a l identique dans les deux cas).
- `8859-1` : `iso-8859-1`.
- une valeur purement numerique (`1252`, `850`, ...) : `cp<valeur>`.
- toute autre valeur : ne pas planter, retomber sur `cp1252` et signaler l en-tete inconnu.

Cette regle ne change rien pour un fichier conforme qui declare `CHARSET:1252` ou `CHARSET:8859-1`: seules les branches `NONE` et inconnue sont nouvelles.

## Reserve

Le rapport #171 attribue le fichier a E*Trade; #154 et #163 decrivent exactement la meme paire de lignes sans nommer d institution, et l auteur de #163 dit l avoir vue chez deux etablissements differents. L attribution E*Trade tient donc a un seul rapporteur. Les octets de la fixture sont reconstruits: seules les deux lignes d en-tete citees sont attestees, le corps est le gabarit commun du corpus. Le fichier de #154 declarait `VERSION:160`, la fixture porte `VERSION:102`, la mesure n etablit donc rien sur la version 1.6. Enfin, la question de savoir si `NONE` est une valeur legale de `CHARSET` dans la specification OFX 1.x n est pas tranchee par les sources reunies ici: l auteur de #163 la qualifie de charset invalide, ce qui n engage que lui, et aucune des trois sources ne cite le texte de la spec. La regle proposee ci-dessus est ecrite pour ne pas dependre de cette reponse.
