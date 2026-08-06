# Banque non nommee: date de solde remplie a `00000000`

- Banque: non nommee (Bresil)
- Format: OFX 1.0.2 SGML
- Fixture: `date-a-zero.ofx`
- Sources: jseutter/ofxparse #179 (PR, ouverte le 2024-11-04)
- Provenance: seule la ligne `<DTASOF>00000000` du bloc `<LEDGERBAL>` vient des octets cites dans la source, c est-a-dire de la fixture ajoutee par la PR. Tout le reste (en-tete, signon, compte, transaction, `<AVAILBAL>` et sa date valide) vient du gabarit commun du corpus. Le Bresil est atteste par la source (`CURDEF` BRL, `LANGUAGE` POR, `BANKID` a quatre chiffres), pas par les octets de la fixture, qui portent les valeurs neutres du gabarit.

## La deviation

La specification OFX 1.0.2 impose pour tout champ de type date le format `YYYYMMDD` eventuellement suivi de l heure. `00000000` ne designe aucune date: ni annee, ni mois, ni jour. La banque s en sert comme d un marqueur de valeur absente sur la date du solde comptable, la ou la specification demanderait soit une date reelle, soit rien du tout. Ici la banque est en tort, pas le parseur qui refuse. Le detail qui compte pour un integrateur: la deviation ne touche que `<LEDGERBAL>`, le bloc `<AVAILBAL>` de la meme fixture porte une date valide, donc un fichier peut melanger les deux formes.

Ce que dit la source:

```
<DTASOF>00000000
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | echec: `OFXSpecError: Can't set LEDGERBAL.dtasof to 00000000: '00000000' does not conform to OFX formats for <class 'datetime.datetime'>` |

ofxtools refuse le fichier entier, avec un message qui nomme le champ fautif et sa valeur: rien ne sort, mais rien de faux non plus. ofxparse accepte le fichier dans les deux modes et rend la transaction complete, sans lever ni avertir. La transaction, elle, est intacte: le montant et la date de l ecriture sont justes, la valeur douteuse reste cantonnee au solde.

## La regle

Avant de convertir un champ de date OFX, tester si la valeur, une fois les espaces coupes, ne contient que des zeros (`^0+$`, ce qui couvre la forme sur huit chiffres comme celle sur quatorze). Dans ce cas, ne pas convertir: poser la date a nul, conserver le montant du solde, et marquer le champ comme absent dans le rapport d import. Ne jamais substituer la date du jour, l epoch, ni la date de fin de releve: une date inventee sur un solde se propage silencieusement dans un rapprochement. Si l application exige une date de solde, refuser le solde, pas le fichier: les transactions restent exploitables. Un fichier conforme n est pas touche, aucune date reelle ne s ecrit avec des zeros seuls.

## Reserve

Deux points ne sont pas etablis. D abord, la source ne parle pas de cette deviation: la PR #179 traite d une ligne vide avant l en-tete et de contenu non-ASCII, et le `<DTASOF>00000000` n arrive que comme detail de la fixture jointe, sans un mot de l auteur ni assertion de test dessus. La deviation est donc attestee par des octets reels, mais aucun rapporteur n a decrit de plantage a son sujet, et notre mesure confirme qu ofxparse n en plante pas. Ensuite, la mesure ne dit rien de la valeur qu ofxparse attribue a la date du solde: elle porte sur les transactions, pas sur `LEDGERBAL`. Que la date soit rendue nulle, absente ou fausse chez ofxparse reste a mesurer avant d en tirer une conclusion. La banque n est pas nommee, seul le pays est deductible de la source.
