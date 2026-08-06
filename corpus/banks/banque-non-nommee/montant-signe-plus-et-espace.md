# Banque non nommee: un montant ecrit `+1 006,60`, signe plus explicite, espace de milliers et virgule decimale

- Banque: non nommee
- Format: OFX 1.0.2 SGML
- Fixture: `montant-signe-plus-et-espace.ofx`
- Sources: jseutter/ofxparse #173 (PR, ouverte le 2023-11-27)
- Provenance: seule la ligne `<TRNAMT>+1 006,60` vient des octets cites dans la source, reprise du cas de test ajoute par la PR. Tout le reste (entete, signon, compte, dates, soldes) vient du gabarit commun du corpus. Le fichier de releve d origine n a jamais ete publie, le rapporteur n en a montre qu un fragment de transaction.

## La deviation

Le montant de la transaction est ecrit `+1 006,60`: signe plus explicite en tete, espace comme separateur de milliers, virgule comme separateur decimal. Un parseur qui passe la valeur telle quelle a un constructeur de decimal echoue sur les trois caracteres a la fois. La virgule decimale est une tolerance ancienne et courante en OFX europeen, deja geree par ofxparse avant cette PR. Le signe plus et l espace de milliers, eux, ne correspondent a aucune ecriture prevue par le type montant d OFX 1.0.2: c est ici la banque qui est en tort, pas le parseur. La note ne s appuie sur aucune ligne de la specification lue directement, voir la reserve.

Ce que dit la source:

```
+    def testThatParseTransactionWithSpaces(self):
+        " Parse numbers with a space separating the thousands. "
+ <TRNAMT>+1 006,60
+ <TRNAMT>+1,006.60
```

```
+        # Handle 1 025,53 formatted numbers
+        d = d.replace(' ', '')
+        # Handle +1058,53 formatted numbers
+        d = d.replace('+', '')
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | passe, 1 transaction, montant `1006.60` |
| `ofxparse` 0.21, fichier ouvert en binaire | passe, 1 transaction, montant `1006.60` |
| `ofxtools` 1.1.1 | echec, `InvalidOperation: [<class 'decimal.ConversionSyntax'>]` |

ofxparse 0.21 lit la valeur sans lever et rend `1006.60`, parce que la correction portee par cette PR est deja dans la version publiee: l espace et le signe plus sont retires avant conversion. ofxtools 1.1.1 refuse le fichier entier avec une erreur de conversion decimale. Aucun des deux ne perd le champ en silence: soit le montant est correct, soit le chargement s arrete.

## La regle

Avant toute conversion en decimal, normaliser le contenu textuel de `TRNAMT` et `BALAMT`:

1. retirer les espaces internes et de bordure, y compris l espace insecable U+00A0 et l espace fine insecable U+202F.
2. si le premier caractere est `+`, le retirer et retenir le signe positif. Si c est `-`, le conserver.
3. si la chaine contient a la fois `.` et `,`, le dernier des deux caracteres rencontres est le separateur decimal, l autre est un separateur de milliers a supprimer. Si elle ne contient que `,`, remplacer cette virgule par un point. Si elle ne contient que `.`, ne rien changer.
4. convertir en decimal exact, jamais en flottant.

Un montant conforme du type `-10.00` ou `1234.56` traverse ces quatre etapes inchange, la regle ne casse donc pas un fichier conforme.

## Reserve

La banque n est pas nommee et le pays n est pas atteste, l ecriture (virgule decimale, espace de milliers) suggere une origine europeenne mais rien dans la source ne le dit. Les octets de la fixture sont reconstruits sur le gabarit commun, seule la ligne du montant est d origine, et elle vient d un cas de test ecrit par le rapporteur, pas d un releve bancaire capture. La proprieteest attestee par une seule personne, en 2023. La conformite a la specification OFX 1.0.2 est affirmee ici de memoire, aucune ligne de la specification n a ete relue pour cette note: a verifier avant de citer ce point ailleurs. La mesure ne contredit pas la source, elle confirme que la correction proposee par la PR est bien presente dans ofxparse 0.21.
