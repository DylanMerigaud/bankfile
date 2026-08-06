# Banque non nommee: balises vides fermees explicitement sur CURDEF, FITID et NAME

- Banque: non nommee (Australie)
- Format: OFX 1.0.2 SGML
- Fixture: `balises-vides-curdef-fitid-name.ofx`
- Sources: jseutter/ofxparse #81 (issue, ouverte le 2015-06-11), commentaire de bruny du 2018-08-03 (liste des champs vides et trace d appel), commentaire de bruny du 2018-08-09 (extraits de `STMTTRN`)
- Provenance: trois lignes portent la deviation, `<CURDEF></CURDEF>`, `<FITID></FITID>` et `<NAME></NAME>`. Les deux dernieres viennent des octets cites par le rapporteur; `CURDEF` vient de la liste de champs vides qu il donne et de la trace d appel qui pointe `account.curdef`, pas d un extrait litteral. Tout le reste (en-tete, signon, bloc de compte, dates, montants, soldes) vient du gabarit commun du corpus. Les balises hors specification presentes dans le meme extrait de l issue (`VALUEDATE`, `CATEGORY`, `TRANSACTIONSPLIT`) sont isolees dans une autre fixture: elles ne sont pas la deviation ici.

## La deviation

Le fichier ferme explicitement trois elements en les laissant vides: `<CURDEF></CURDEF>` dans le `STMTRS`, `<FITID></FITID>` et `<NAME></NAME>` dans une transaction. La forme est double: une balise fermante explicite (licite dans le profil SGML d OFX 1.x, ou la fermeture des elements de donnees est facultative mais permise) et un contenu vide. C est le contenu vide qui sort de la specification: `CURDEF` attend un code devise a trois lettres et `FITID` un identifiant non vide, tous deux obligatoires dans un releve bancaire. Ici la banque est en tort sur la valeur, pas le parseur qui refuse le fichier. La question reste ouverte cote parseur pour la tolerance: un champ vide et un champ absent devraient se traiter pareil, ce que demande le rapporteur, et ofxparse plante sur le vide alors qu il tolere l absent.

Ce que dit la source:

```
 <FITID></FITID>
 <NAME></NAME>
```

```
    account.curdef = act_curdef.contents[0].strip()
IndexError: list index out of range
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | echec: `IndexError: list index out of range` |
| `ofxparse` 0.21, fichier ouvert en binaire | echec: `IndexError: list index out of range` |
| `ofxtools` 1.1.1 | echec: `OFXSpecError: Can't set STMTTRN.fitid to None: String: Value is required` |

Les trois lectures echouent, aucune ne rend de transaction: pas de perte silencieuse ici, le fichier ne passe nulle part. ofxtools nomme le champ fautif et la raison, ofxparse leve une `IndexError` nue qui n indique ni le champ ni la ligne, exactement le message que le rapporteur montrait en 2018 sur la version 0.18. Le pronostic laisse en 2016 dans l issue ("this will go away" apres la fusion de #108) est dementi par la mesure: huit ans et plusieurs versions plus tard, le cas plante toujours.

## La regle

Traiter un element vide comme un element absent, avant toute lecture de valeur: apres extraction du contenu textuel, une chaine vide ou uniquement blanche vaut `None`, quelle que soit la forme d ecriture (`<TAG></TAG>`, `<TAG/>`, ou `<TAG>` immediatement suivi de la balise suivante en SGML). Ensuite, appliquer la regle du champ manquant propre a chaque element: `NAME`, `CHECKNUM`, `REFNUM` vides restent vides et la transaction est rendue; `FITID` vide fait tomber la transaction sur son identifiant de repli (empreinte date + montant + memo) au lieu de lever; `CURDEF` vide herite de la devise du compte ou, a defaut, laisse le champ non renseigne et signale un avertissement, jamais une exception. Un fichier conforme ne rencontre aucun de ces chemins, puisque ses elements portent tous une valeur.

## Reserve

La banque n est pas nommee. Le pays, l Australie, vient de la seule declaration du rapporteur ("2 x separate OFX files from Australian banks") et n est atteste par personne d autre; il porte sur les fichiers de 2018, pas sur celui du signalement initial de 2015, dont l auteur est un tiers et dont la banque est inconnue. Les octets de la fixture sont reconstruits: seules les trois balises vides viennent de la source, et `CURDEF` vide n est meme pas cite litteralement, il est deduit de la liste de champs et de la trace d appel. La forme d ecriture est un choix de reconstruction: le rapporteur montre `<FITID></FITID>` dans un extrait et `<FITID>` sans fermeture dans un autre, la fixture retient la premiere. Enfin, la mesure donne le message d erreur d ofxparse mais pas sa pile: rien dans notre mesure ne prouve que la 0.21 echoue sur la meme ligne `account.curdef` qu en 2018, seul le message coincide.
