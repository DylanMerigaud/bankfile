# Banque non nommee: une ligne vide precede la premiere ligne d entete

- Banque: non nommee (Bresil)
- Format: OFX 1.0.2 SGML
- Fixture: `ligne-vide-avant-entete.ofx` (UTF-8, alors que l entete declare `ENCODING:USASCII` et `CHARSET:1252`)
- Sources: jseutter/ofxparse #161 (PR, ouverte le 2020-11-22), jseutter/ofxparse #179 (PR, ouverte le 2024-11-04)
- Provenance: la ligne vide initiale et le contenu non ASCII du libelle viennent des octets cites dans les PR (la fixture jointe a #179 commence par une ligne vide et porte un `<MEMO>` accentue). Tout le reste, arborescence, montants, dates, identifiants, vient du gabarit commun du corpus; les valeurs de compte sont neutralisees.

## La deviation

Le fichier commence par une ligne vide, puis vient `OFXHEADER:100` et le reste du bloc d entete. Le corps du releve porte en plus un caractere accente dans un `<MEMO>`, alors que l entete annonce `ENCODING:USASCII`. La specification OFX 1.x decrit un bloc d entete termine par une ligne vide avant le contenu SGML, mais elle n interdit pas d espace blanc en tete de fichier, et un lecteur tolerant doit ignorer les lignes vides de tete. Le fichier est donc a considerer comme acceptable, et le defaut historique est du cote du parseur: `ofxparse` bouclait sur les lignes de l entete et sortait de la boucle a la premiere ligne vide, ce qui, avec une ligne vide en position zero, vidait l entete entiere. Les deux PR corrigent exactement ce point en remplacant la sortie de boucle par une continuation.

Ce que dit la source:

```
My bank OFX files start with empty lines, this PR fixes parsing of those files.
             if line.strip() == six.b(""):
-                break
+                continue
<MEMO>TRANSFERENCIA PIX DES: Laboratório Hacker De 18/10
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | echec: `UnicodeDecodeError: 'ascii' codec can't decode byte 0xd3 in position 648: ordinal not in range(128)` |
| `ofxparse` 0.21, fichier ouvert en binaire | echec: `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 648: ordinal not in range(128)` |
| `ofxtools` 1.1.1 | succes: 1 transaction, `TRNAMT` = `-10.00`, `FITID` = `T0001` |

Les deux appels a `ofxparse` echouent bruyamment, et sur le caractere accente, pas sur la ligne vide: le decodage ASCII derive de l entete `ENCODING:USASCII` casse avant que le contenu ne soit interprete. `ofxtools` lit le fichier sans se plaindre et rend la transaction complete. Aucun des trois n a rendu de champ ampute en silence sur cette fixture.

## La regle

A la lecture, retirer les lignes vides et les lignes uniquement blanches situees avant la premiere ligne d entete, puis analyser l entete normalement; ne considerer comme fin de bloc d entete que la premiere ligne vide qui suit au moins une ligne `CLE:VALEUR`. Un fichier conforme, sans ligne vide de tete, traverse cette regle inchange. La regle est purement lexicale et ne touche pas au corps SGML.

## Reserve

La banque n est pas nommee dans les sources, seule la langue et le libelle en portugais rattachent la fixture au Bresil, c est une deduction, pas une attestation. Les octets sont reconstruits: seule la structure de tete et le libelle accente proviennent de la source, le reste est le gabarit du corpus. Surtout, la mesure ne reproduit pas le symptome decrit par les rapporteurs: ils decrivent une entete perdue a cause de la ligne vide, alors que `ofxparse` 0.21 s arrete ici plus tot, sur le decodage ASCII du libelle accente. Le comportement de `ofxparse` face a la ligne vide seule n est donc pas etabli par cette fixture, il faudrait une variante sans caractere accente pour l isoler. Enfin, deux PR distinctes (2020 et 2024) proposent la meme correction, ce qui atteste la recurrence du cas, mais aucune n a de mesure d execution attachee ici.
