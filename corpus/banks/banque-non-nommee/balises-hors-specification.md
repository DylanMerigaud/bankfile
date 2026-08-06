# Banque non nommee: des balises maison glissees dans une transaction

- Banque: non nommee (Australie)
- Format: OFX 1.0.2 SGML
- Fixture: `balises-hors-specification.ofx`
- Sources: jseutter/ofxparse #81 (issue, ouverte le 2015-06-11), extrait de transaction publie en commentaire par bruny le 2018-08-09
- Provenance: les trois balises hors specification viennent des octets cites dans l issue; tout le reste (entete, signon, compte, montants, dates, solde) vient du gabarit commun du corpus, et le style SGML sans balise fermante est celui du gabarit, pas celui de l extrait cite.

## La deviation

Le `<STMTTRN>` porte trois balises qui n existent pas dans la specification OFX 1.0.2: `VALUEDATE`, `TRANSACTIONSPLIT` et `CATEGORY`. Elles sont placees entre les champs standards, apres `MEMO`, a l interieur de l agregat de transaction. La specification definit la liste fermee des enfants de `STMTTRN`, donc ce fichier n est pas conforme: la banque ajoute ici son propre vocabulaire, ce n est pas un parseur trop strict qui a tort. Le probleme pratique n est pas la conformite mais la robustesse: un parseur qui traite un enfant inconnu comme une erreur, ou pire qui decale sa lecture des champs suivants, rend une transaction fausse a partir d un fichier par ailleurs lisible.

Ce que dit la source:

```
 <VALUEDATE>20180801</VALUEDATE>
 <TRANSACTIONSPLIT>No</TRANSACTIONSPLIT>
 <CATEGORY>Uncategorised</CATEGORY>
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction, debit, montant `-10.00`, date `2026-01-15 00:00:00`, payee `ANON MERCHANT`, memo `ANON MEMO`, checknum vide |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction, debit, montant `-10.00`, date `2026-01-15 00:00:00`, payee `ANON MERCHANT`, memo `ANON MEMO`, checknum vide |
| `ofxtools` 1.1.1 | 1 transaction, `STMTTRN(trntype='DEBIT', dtposted=2026-01-15 UTC, trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT', memo='ANON...` |

Aucun des trois parseurs n echoue, et aucun ne se decale: les champs standards de la transaction sont rendus avec les bonnes valeurs dans les trois cas. Les trois balises maison sont ignorees en silence, ce qui est sans consequence sur le rapprochement tant que la donnee utile reste dans les champs standards; en revanche l information portee par `VALUEDATE` et `CATEGORY` est perdue sans le moindre avertissement.

## La regle

A l interieur d un agregat OFX connu, un element enfant dont le nom n appartient pas a la liste de la specification doit etre lu, saute, et enregistre dans un sac d extensions attache a l agregat (nom de balise, valeur brute), jamais provoquer une erreur ni interrompre la lecture des enfants suivants. La lecture reprend au frere suivant, sans remonter d un niveau. Un fichier conforme ne comporte aucun enfant inconnu, donc ce sac reste vide et le traitement est inchange. Si un compteur d extensions est expose, le journaliser une fois par fichier plutot que par transaction.

## Reserve

La banque n est pas nommee et le pays (Australie) tient a une seule declaration du rapporteur dans l issue, non verifiee. Les octets de la fixture sont reconstruits: seules les trois lignes citees viennent de la source, le reste est le gabarit du corpus, et l extrait d origine ecrivait ses balises avec fermeture explicite alors que la fixture suit le style SGML sans fermeture. Surtout, la mesure contredit le recit de l issue: #81 rapporte des plantages (`IndexError: list index out of range`) mais ceux-ci concernent des balises standards a contenu VIDE, pas des balises inconnues; sur ce point precis, les trois parseurs mesures ici passent sans erreur. Ce cas documente donc une perte silencieuse de champ, pas un plantage. Le rapport date de 2018, sur ofxparse 0.18.
