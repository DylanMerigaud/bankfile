# OnPoint Community Credit Union: un MEMO ecrit en balise auto-fermante `<MEMO/>` dans un fichier SGML

- Banque: OnPoint Community Credit Union (Etats-Unis)
- Format: OFX 1.0.2 SGML
- Fixture: `balise-auto-fermante-memo.ofx`
- Sources: jseutter/ofxparse #167 (issue, ouverte le 2022-04-24), jseutter/ofxparse #81 (issue, ouverte le 2015-06-11)
- Provenance: le token `<MEMO/>` vient des octets cites dans l issue #167; tout le reste du fichier (entete, signon, compte fictif, montant, dates, soldes) vient du gabarit commun anonymise. Seule cette ligne differe du gabarit.

## La deviation

Le fichier declare `VERSION:102`, donc de l OFX 1.0.2, qui est du SGML: un element sans valeur ne s ecrit pas, il s omet. La banque ecrit ici `<MEMO/>`, la forme auto-fermante empruntee au XML, celle que l OFX 2.x autorise. Le fichier n est donc pas conforme a la version qu il declare lui-meme, et la faute est du cote de la banque, pas du parseur. Un lecteur SGML naif voit une balise ouvrante nommee `MEMO/`, ou une balise ouvrante jamais fermee, et le desequilibre se propage a tout ce qui suit dans l agregat. L issue #81 rapporte la meme forme chez une autre banque et sur d autres champs (`<ORG/>`, `<FID/>`), ce qui indique un motif recurrent et pas un accident isole d un seul emetteur.

Ce que dit la source:

```
tokens that look like <MEMO/> cause OfxPreprocessedFile() to set is_closing_tag=false and is_open_tag=true which, in turn causes re.findall() to fault. This flavor of token appears in the ofx file from my credit union, onpointcu.com. It may be encoded wrong, but the right fix would be a better parse code that does not allow the code to fault.
```

Et #81, sur la meme forme:

```
The empty tag syntax is valid XML but the parser doesn't like it.
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction, debit, montant `-10.00`, payee `ANON MERCHANT`, memo vide |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction, debit, montant `-10.00`, payee `ANON MERCHANT`, memo vide |
| `ofxtools` 1.1.1 | echec: `OFXSpecError: Can't set STMTRS.ledgerbal to None: SubAggregate: Value is required` |

`ofxparse` 0.21 ne plante plus: il rend la transaction complete et le memo comme chaine vide, ce qui est le bon comportement puisque la balise ne portait aucune valeur. `ofxtools` 1.1.1 echoue, et son message ne nomme pas `MEMO` mais `LEDGERBAL`, un element situe bien plus loin dans le fichier: l erreur remonte a la surface loin de la ligne qui la cause, et c est tout le releve qui est perdu, pas seulement le champ. Aucun des trois n a rendu de transaction amputee en silence.

## La regle

Avant d envoyer un fichier a un parseur, si l entete annonce `VERSION:1xx` (SGML), passer le corps par une tokenisation de balises et, pour chaque token qui correspond exactement a `<[A-Za-z0-9_.]+/>`, le supprimer: un element auto-fermant ne porte par construction aucune valeur, et son absence est deja le cas nominal en OFX 1.x. N appliquer la substitution qu aux tokens entiers reconnus comme balises, jamais a une occurrence de `/>` trouvee a l interieur d une valeur de champ. Ne rien faire sur un fichier OFX 2.x: la forme y est legale et le lecteur XML la traite correctement. Sur un fichier 1.x conforme, aucun token ne correspond au motif, donc la regle est sans effet.

## Reserve

Les octets de la fixture sont reconstruits: seul le token `<MEMO/>` est atteste par la source, le releve autour vient du gabarit commun et ne provient pas d un fichier OnPoint reel. Le champ porteur choisi est celui de l issue (`MEMO`), alors que #81 montre la meme forme sur `ORG` et `FID`; la fixture ne couvre donc qu une instance d une famille plus large. Point important: la source decrit un plantage de `OfxPreprocessedFile()` que la mesure ne reproduit pas, `ofxparse` 0.21 (posterieur au rapport de 2022) traite le cas sans lever. La deviation reste reelle cote fichier, mais le comportement decrit dans l issue est celui d une version ancienne, pas de celle qui est mesuree ici.
