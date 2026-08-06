# Phase 0: le depouillement des 43 entrees ouvertes d `ofxparse`

> Fait le 2026-08-05. Ce document est la trace complete du tri, entree par entree. Il existe
> pour deux raisons: que personne n ait a refaire le depouillement, et que chaque fixture du
> corpus remonte a une source qu un lecteur peut ouvrir.

Le premier livrable de ce depot est le corpus, pas le parseur. Un modele ecrit un parseur
conforme a une specification publique en trente secondes; il ne peut pas savoir que Wells Fargo
ecrit tout son en-tete QFX sur une seule ligne. Ce sont des faits sur le monde, ils se
constatent, ils ne se deduisent pas.

## Ce que compte le nombre 43

`jseutter/ofxparse` porte, au 2026-08-05, **33 issues et 10 PR ouvertes**. Les PR comptent, et
elles comptent meme double: une PR non fusionnee porte souvent les OCTETS exacts du fichier qui
a casse, dans sa fixture de test. Trois des exemples du brief sont d ailleurs des PR jamais
fusionnees: #172 (Wells Fargo), #160 (Chase), #163 (`cpNONE`).

## Le resultat

| | |
|---|---|
| entrees depouillees | 43 |
| entrees portant une deviation de fichier attestee | 15 |
| fixtures produites | 17 |
| banques nommees dans les sources | 6 |
| entrees sans propriete de fichier | 28 |

Quinze entrees pour dix-sept fixtures: plusieurs entrees decrivent la meme deviation (les trois
sources de `CHARSET:NONE` sont fusionnees en une fixture), et deux entrees en portaient
plusieurs a la fois (la PR #179 apporte a elle seule trois deviations distinctes, la PR #173
deux).

**Six banques sur dix-sept cas seulement portent un nom.** C est ce que les sources autorisent:
les autres rapporteurs ecrivent "my bank" et rien de plus. Inventer les onze autres aurait ete
plus joli et aurait detruit l actif.

## Les 43, une par une

Verdict `fixture` veut dire que l entree a produit au moins un cas du corpus. Les autres
portent la raison du rejet: le critere est unique et il est ecrit une fois pour toutes,
**la source doit attester une propriete du CONTENU d un fichier**. Une demande de
fonctionnalite, aussi legitime soit-elle, n en est pas une.

| # | type | titre | verdict |
|---|---|---|---|
| [182](https://github.com/jseutter/ofxparse/issues/182) | issue | Maintenance status of ofxparse | question ou entree vide |
| [181](https://github.com/jseutter/ofxparse/pull/181) | PR | Remove bs4 deprecation warnings | documentation ou maintenance du depot |
| [180](https://github.com/jseutter/ofxparse/issues/180) | issue | There is a bug in ofxparse, owned by jseutter | question ou entree vide |
| [179](https://github.com/jseutter/ofxparse/pull/179) | PR | Fix import OFX file with linebreak before headers and not A... | **fixture** `banque-non-nommee/ligne-vide-avant-entete, montant-virgule-decimale, date-a-zero` |
| [177](https://github.com/jseutter/ofxparse/pull/177) | PR | trim usage of six | documentation ou maintenance du depot |
| [176](https://github.com/jseutter/ofxparse/issues/176) | issue | Feature Request - Add Transaction Parsing for "DTAVAIL" Fie... | couverture de la specification, pas une deviation |
| [175](https://github.com/jseutter/ofxparse/pull/175) | PR | Add writer of Credit Card Statement | fonctionnalite de la librairie |
| [173](https://github.com/jseutter/ofxparse/pull/173) | PR | Handle `chknum` in transaction field | **fixture** `banque-non-nommee/chknum-au-lieu-de-checknum, montant-signe-plus-et-espace` |
| [172](https://github.com/jseutter/ofxparse/pull/172) | PR | The header in a Wells Fargo  .qfx file contains no newlines | **fixture** `wells-fargo/entete-sans-retour-ligne` |
| [171](https://github.com/jseutter/ofxparse/issues/171) | issue | Bug with encoding for ETrade | **fixture** `etrade/charset-none-avec-encoding-usascii` |
| [170](https://github.com/jseutter/ofxparse/issues/170) | issue | XMLParsedAsHTMLWarning | bug Python interne, aucune propriete de fichier |
| [169](https://github.com/jseutter/ofxparse/issues/169) | issue | Cannot process UTF-8 files with characters outside the 256 ... | **fixture** `banque-non-nommee/caractere-hors-latin1` |
| [167](https://github.com/jseutter/ofxparse/issues/167) | issue | OfxPreprocessedFile() crashes on an empty close tag like th... | **fixture** `onpoint-community-credit-union/balise-auto-fermante-memo` |
| [166](https://github.com/jseutter/ofxparse/issues/166) | issue | Does this parse ofx 1.0 format? | question ou entree vide |
| [164](https://github.com/jseutter/ofxparse/issues/164) | issue | Missing BANKACCTTO on statement transaction | couverture de la specification, pas une deviation |
| [163](https://github.com/jseutter/ofxparse/pull/163) | PR | Fixing parse error "unknown encoding: cpNONE" | **fixture** `etrade/charset-none-avec-encoding-usascii` |
| [162](https://github.com/jseutter/ofxparse/issues/162) | issue | Transaction that is not a DEBIT nor a CREDIT | **fixture** `lcl/trntype-check-sans-payee` |
| [161](https://github.com/jseutter/ofxparse/pull/161) | PR | Allow parsing OFX files starting with empty lines | **fixture** `banque-non-nommee/ligne-vide-avant-entete` |
| [160](https://github.com/jseutter/ofxparse/pull/160) | PR | Support parsing quirky Chase QFX headers | **fixture** `chase/entete-ligne-vide-initiale-sans-separation` |
| [159](https://github.com/jseutter/ofxparse/issues/159) | issue | Read an OFX String instead of a OFX file | fonctionnalite de la librairie |
| [158](https://github.com/jseutter/ofxparse/issues/158) | issue | transaction.security and position.security should be Securi... | couverture de la specification, pas une deviation |
| [154](https://github.com/jseutter/ofxparse/issues/154) | issue | OfxParser.parse fails: unknown encoding: cpNONE | **fixture** `etrade/charset-none-avec-encoding-usascii` |
| [149](https://github.com/jseutter/ofxparse/issues/149) | issue | Changing <FITID> is not persisting at all | fonctionnalite de la librairie |
| [148](https://github.com/jseutter/ofxparse/issues/148) | issue | Not able to read file with iso-8859-1 encoding | **fixture** `banque-non-nommee/charset-8859-1-sans-prefixe-iso` |
| [145](https://github.com/jseutter/ofxparse/issues/145) | issue | 'str' object has no attribute 'strftime' in ofxprinter | bug Python interne, aucune propriete de fichier |
| [144](https://github.com/jseutter/ofxparse/pull/144) | PR | Generic ofx2dataframe converter capable of handling multipl... | fonctionnalite de la librairie |
| [142](https://github.com/jseutter/ofxparse/issues/142) | issue | Python3 "TypeError: must be str, not bytes" | bug Python interne, aucune propriete de fichier |
| [136](https://github.com/jseutter/ofxparse/issues/136) | issue | Transaction Date, Value, Memo | question ou entree vide |
| [133](https://github.com/jseutter/ofxparse/issues/133) | issue | UTF-8 Encoding | **fixture** `banque-non-nommee/declaration-xml-ofx-2` |
| [128](https://github.com/jseutter/ofxparse/issues/128) | issue | Can not add own field in Transaction Object | fonctionnalite de la librairie |
| [125](https://github.com/jseutter/ofxparse/issues/125) | issue | travis.yml should not specify BeautifulSoup for Python 2.7 | documentation ou maintenance du depot |
| [124](https://github.com/jseutter/ofxparse/issues/124) | issue | Currency on transactions | couverture de la specification, pas une deviation |
| [81](https://github.com/jseutter/ofxparse/issues/81) | issue | Empty tags | **fixture** `banque-non-nommee/balises-vides-curdef-fitid-name, trntype-en-casse-mixte, balises-hors-specification, onpoint/balise-auto-fermante-memo` |
| [70](https://github.com/jseutter/ofxparse/issues/70) | issue | [easy] PEP8 code style cleanup | documentation ou maintenance du depot |
| [58](https://github.com/jseutter/ofxparse/issues/58) | issue | [medium] Parse dates in %d%m%y format | **fixture** `hsbc-brasil/dtstart-format-ddmmyy` |
| [57](https://github.com/jseutter/ofxparse/issues/57) | issue | [medium] Use coveralls.io to generate test coverage stats | documentation ou maintenance du depot |
| [50](https://github.com/jseutter/ofxparse/issues/50) | issue | [easy] README file does not show attributes of transactions | documentation ou maintenance du depot |
| [29](https://github.com/jseutter/ofxparse/issues/29) | issue | [easy] FTIDs in test fixtures should be unique | documentation ou maintenance du depot |
| [17](https://github.com/jseutter/ofxparse/issues/17) | issue | [medium] Application script: Convert an OFX file to a set o... | fonctionnalite de la librairie |
| [16](https://github.com/jseutter/ofxparse/issues/16) | issue | [medium] Application script: Convert an OFX file to a .json... | fonctionnalite de la librairie |
| [15](https://github.com/jseutter/ofxparse/issues/15) | issue | [medium] Application script: Convert an OFX file to a CSV file | fonctionnalite de la librairie |
| [14](https://github.com/jseutter/ofxparse/issues/14) | issue | [hard] Document how to make a release | documentation ou maintenance du depot |
| [5](https://github.com/jseutter/ofxparse/issues/5) | issue | [medium] ofxparse wiki pages | documentation ou maintenance du depot |

## Quatre entrees, une seule cause

`#160` (Chase), `#161`, `#169` et `#179` decrivent quatre fichiers differents et un seul bug:
`read_headers` coupe l en-tete au premier `<` puis s arrete a la premiere ligne vide. Une ligne
vide en tete de fichier, et TOUS les en-tetes sont perdus en silence. Le fichier se lit quand
meme tant qu il ne contient que de l ASCII, et casse des le premier octet accentue, ce qui
explique pourquoi les rapports se contredisent en apparence.

C est le genre de fait qu on ne voit qu en depouillant les 43 d un coup, et c est un argument
direct pour la couche d unification: une regle ecrite une fois couvre quatre banques.

## Ce que ce depouillement ne prouve pas

- **Le corpus ne contient aucune deviation MT940, CAMT.053 ou BAI2.** Les 43 entrees sont
  OFX/QFX, parce que la source depouillee est un parseur OFX. La phase 1 porte MT940 ET
  OFX/QFX: la moitie MT940 du corpus reste entierement a constituer, et elle ne sortira pas de
  ce tracker.
- **Aucune fixture n est un fichier de banque reel en notre possession.** Toutes sont
  reconstruites a partir de textes publics, sur un gabarit commun, pour que le diff avec le
  gabarit soit exactement la deviation. Chaque note dit ce qui vient des octets cites et ce qui
  vient du gabarit.
- **Certaines deviations reposent sur un seul rapport, parfois ancien.** HSBC Brasil date de
  2013 et n a jamais ete reconfirme. La note le dit.
- **Une fixture qui ne casse aucun des deux parseurs n est pas une preuve d inutilite, ni
  l inverse.** Trois fixtures passent partout aujourd hui: elles documentent une forme reelle
  et servent de garde-fou a notre propre parseur.

## Les pistes que ce depouillement laisse ouvertes

- **#166 nomme Citi Australia** et decrit un OFX 1.0 "odd" qui echoue, sans jamais donner les
  octets. C est la seule banque nommee du tracker dont il manque le fichier: une question dans
  l issue suffirait a la recuperer.
- **Quatre entrees demandent des champs de la specification qu `ofxparse` n expose pas**
  (`DTAVAIL` #176, `BANKACCTTO` et `CCACCTTO` #164, `CURRENCY` et `CURRATE` #124, l objet
  `Security` #158). Ce ne sont pas des deviations, un modele les deduit de la specification.
  C est en revanche une liste de champs que des fichiers reels portent vraiment, donc une
  entree directe pour le schema normalise de la phase 1.
- **#29 est un avertissement adresse a nous.** Les mainteneurs d `ofxparse` ont anonymise leurs
  propres fixtures au point de rendre les `FITID` non uniques, ce qui a casse la propriete que
  la fixture testait. Notre anonymisation doit s arreter avant la propriete testee.
