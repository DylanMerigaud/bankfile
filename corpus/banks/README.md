# Le corpus de deviations, un fichier par banque

C'est l'ACTIF de ce projet. Le code ne l'est pas.

Un modele ecrit un parseur MT940 conforme a la specification en trente secondes, parce que la
specification est publique. Il ne peut pas savoir que Wells Fargo omet les retours a la ligne
dans l'en-tete d'un QFX, que Chase ecrit des en-tetes tordus, ou qu'une banque emet `cpNONE`
comme encodage. Ce sont des faits sur le monde et non sur la norme: ils ne se deduisent pas,
ils se constatent.

Ces trois exemples ne sont pas inventes, ils sont tires des issues ouvertes et non traitees de
`jseutter/ofxparse` (#172, #160, #163), un paquet a 191878 telechargements mensuels dont la
derniere version date du 31 mai 2021.

## La regle

Un fichier par deviation, anonymise, avec un `.md` a cote qui dit la banque, le format, ce qui
devie de la norme, et la reference de la source (issue, rapport d'utilisateur).

Anonymisation: montants, noms et numeros de compte remplaces. **La structure est la donnee, le
contenu ne l'est jamais.**

Deux limites que `scripts/validate_corpus.py` fait respecter, parce qu'elles sont faciles a
oublier dans un extrait colle depuis un vrai fichier: aucune suite de 13 a 19 chiffres (un
horodatage OFX complet en fait 14, utilisez la date seule), et aucun motif d'IBAN. La regle
s'applique AUSSI aux notes: elles citent des issues publiques, et une issue publique contient
parfois un vrai numero de compte.

Troisieme limite, apprise de l'issue #29 d'`ofxparse`: leurs mainteneurs ont anonymise leurs
propres fixtures au point de rendre les `FITID` non uniques, ce qui a detruit la propriete que
la fixture testait. **L'anonymisation s'arrete avant la propriete testee.**

## Une fixture est un gabarit plus une deviation

Toutes les fixtures OFX derivent du meme document minimal, et n'en different que par la
deviation qu'elles portent. C'est delibere: la valeur d'une fixture de corpus vient de ce que
son diff avec le gabarit EST la deviation, et rien d'autre. Ecrites une par une a la main,
elles derivent (un espace ici, une date la) et le diff cesse de dire quoi que ce soit.

## Deux categories, et il faut les distinguer

Toutes les entrees ne sont pas des fautes de la banque, et l'ecrire a tort se retourne contre
le corpus des que quelqu'un ouvre la specification.

- **Le fichier est hors specification.** Wells Fargo colle tout son en-tete sur une ligne, Chase
  supprime la ligne vide de separation. La banque est en tort.
- **Le fichier est conforme et le parseur echoue quand meme.** `CHARSET:NONE` est l'une des
  trois valeurs prevues par OFX 1.x, `CHECK` est un `TRNTYPE` legitime, `NAME` est optionnel.
  C'est le consommateur qui suppose ce que la norme n'a jamais promis.

Les deux comptent autant: dans les deux cas, un fichier reel casse du code reel.

## Les cas

Chaque note porte une mesure datee: ce que `ofxparse` 0.21 et `ofxtools` 1.1.1 font
reellement sur la fixture, execute et non deduit.

| banque | cas | ce que le fichier fait |
|---|---|---|
| Wells Fargo | [entete-sans-retour-ligne](wells-fargo/entete-sans-retour-ligne.md) | tout l'en-tete sur une seule ligne |
| Chase | [entete-ligne-vide-initiale-sans-separation](chase/entete-ligne-vide-initiale-sans-separation.md) | ligne vide avant l'en-tete, aucune apres |
| E*Trade | [charset-none-avec-encoding-usascii](etrade/charset-none-avec-encoding-usascii.md) | `CHARSET:NONE` avec `ENCODING:USASCII` |
| HSBC Brasil | [dtstart-format-ddmmyy](hsbc-brasil/dtstart-format-ddmmyy.md) | `DTSTART` sur six chiffres, JJMMAA |
| LCL | [trntype-check-sans-payee](lcl/trntype-check-sans-payee.md) | un `CHECK` sans `NAME` ni `MEMO` |
| OnPoint Community Credit Union | [balise-auto-fermante-memo](onpoint-community-credit-union/balise-auto-fermante-memo.md) | `<MEMO/>` auto-fermant en SGML |
| non nommee | [caractere-hors-latin1](banque-non-nommee/caractere-hors-latin1.md) | un beneficiaire hors latin-1 |
| non nommee | [charset-8859-1-sans-prefixe-iso](banque-non-nommee/charset-8859-1-sans-prefixe-iso.md) | `CHARSET:8859-1`, sans le prefixe `ISO-` |
| non nommee | [declaration-xml-ofx-2](banque-non-nommee/declaration-xml-ofx-2.md) | OFX 2.x, encodage dans la declaration XML |
| non nommee | [ligne-vide-avant-entete](banque-non-nommee/ligne-vide-avant-entete.md) | une ligne vide precede l'en-tete |
| non nommee | [montant-virgule-decimale](banque-non-nommee/montant-virgule-decimale.md) | `2000,00` |
| non nommee | [montant-signe-plus-et-espace](banque-non-nommee/montant-signe-plus-et-espace.md) | `+1 006,60` |
| non nommee | [date-a-zero](banque-non-nommee/date-a-zero.md) | `DTASOF` rempli de zeros |
| non nommee | [chknum-au-lieu-de-checknum](banque-non-nommee/chknum-au-lieu-de-checknum.md) | `CHKNUM` au lieu de `CHECKNUM` |
| non nommee | [balises-vides-curdef-fitid-name](banque-non-nommee/balises-vides-curdef-fitid-name.md) | balises presentes et vides |
| non nommee | [trntype-en-casse-mixte](banque-non-nommee/trntype-en-casse-mixte.md) | `Credit` au lieu de `CREDIT` |
| non nommee | [balises-hors-specification](banque-non-nommee/balises-hors-specification.md) | des balises maison dans un `STMTTRN` |

Six banques nommees sur dix-sept cas: c'est ce que les sources autorisent, les autres
rapporteurs ecrivent "my bank" et rien de plus. Le detail du tri des 43 entrees est dans
[docs/PHASE0-DEPOUILLEMENT.md](../../docs/PHASE0-DEPOUILLEMENT.md).

**Il n'y a encore aucune deviation MT940, CAMT.053 ou BAI2 ici.** La source depouillee est un
parseur OFX, elle ne pouvait rien produire d'autre.
