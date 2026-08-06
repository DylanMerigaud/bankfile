# Banque non nommee: un TRNTYPE en casse mixte, ferme par une balise fermante explicite

- Banque: non nommee (Australie)
- Format: OFX 1.0.2 SGML
- Fixture: `trntype-en-casse-mixte.ofx`
- Sources: jseutter/ofxparse #81 (issue, ouverte le 2015-06-11), ligne citee apportee par le commentaire de bruny du 2018-08-09
- Provenance: la ligne `<TRNTYPE>Credit</TRNTYPE>` vient telle quelle des octets colles dans l issue. Tout le reste du fichier vient du gabarit commun du corpus (entete, signon, compte, une transaction, soldes), avec des valeurs neutres.

## La deviation

La transaction porte un TRNTYPE ecrit `Credit`, en casse mixte, la ou la specification OFX 1.0.2 enumere les valeurs de ce champ en majuscules (CREDIT, DEBIT, INT, DIV, FEE, et le reste). Le fichier est donc bien en tort sur ce point precis: une valeur enumeree n est pas une chaine libre, et rien dans la specification n autorise a en changer la casse. La balise fermante `</TRNTYPE>`, elle, n est pas une deviation: en OFX 1.x SGML les balises fermantes sont optionnelles sur les elements feuilles, pas interdites, et un parseur qui bute dessus est en tort. Les deux particularites arrivent sur la meme ligne, ce qui rend le cas facile a confondre avec un simple probleme de balise fermante.

Ce que dit la source:

```
<TRNTYPE>Credit</TRNTYPE>
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | passe, 1 transaction, type `credit`, montant `-10.00`, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxparse` 0.21, fichier ouvert en binaire | passe, 1 transaction, type `credit`, montant `-10.00`, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | echec: `OFXSpecError: Can't set STMTTRN.trntype to Credit: 'Credit' is not OneOf ('CREDIT', 'DEBIT', 'INT', 'DIV', 'FEE', 'SRVCHG', 'DEP', 'ATM', 'POS', 'XFER', 'CHECK', 'PAYMENT', 'CASH', 'DIRECTDEP', 'DIRECTDEBIT', 'REPE` |

Les deux modes d ouverture de `ofxparse` donnent le meme resultat et rendent la transaction complete: aucun champ n est perdu, et le type ressort normalise en `credit`. `ofxtools` refuse le fichier entier sur la seule valeur du champ, donc l echec est bruyant et sans risque de montant faux. Aucun des trois parseurs ne rend ici une transaction amputee en silence.

## La regle

Avant toute validation du champ, mettre la valeur de TRNTYPE en majuscules apres suppression des espaces de bord, puis comparer a l enumeration de la specification. Si la valeur ainsi normalisee appartient a l enumeration, l accepter; sinon seulement, lever. Cette normalisation ne change rien pour un fichier conforme, dont les valeurs sont deja en majuscules. Ne jamais deviner une valeur de remplacement pour une chaine hors enumeration, et ne pas rejeter la balise fermante `</TRNTYPE>`, legale en SGML.

## Reserve

Le rapporteur du commentaire de 2018 decrit une famille de plantages liee aux champs vides (`IndexError: list index out of range` sur CURDEF), pas a la casse de TRNTYPE, et la fixture ne reproduit pas ce plantage: sur ces octets isoles, `ofxparse` passe sans rien signaler. La ligne citee est authentique, mais le fichier autour est reconstruit a partir du gabarit du corpus, donc la mise en page reelle du releve d origine (indentation, balises fermantes partout, champs hors specification) n est pas representee ici. La banque n est pas nommee dans l issue; le pays vient de la mention faite par le rapporteur de banques australiennes. Le message d erreur de `ofxtools` est recopie tel qu il figure dans les mesures, ou il est tronque en fin de liste apres `'REPE`. Enfin, le montant `-10.00` associe a un type `credit` est un artefact du gabarit commun, pas une incoherence du cas rapporte.
