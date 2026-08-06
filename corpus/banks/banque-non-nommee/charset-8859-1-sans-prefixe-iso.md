# Banque non nommee: CHARSET declare "8859-1", sans le prefixe "ISO-"

- Banque: non nommee
- Format: QFX, en-tete OFX 1.0.2 SGML
- Fixture: `charset-8859-1-sans-prefixe-iso.qfx`
- Sources: jseutter/ofxparse #148 (issue, ouverte le 2019-03-07)
- Provenance: les deux lignes d en-tete `ENCODING:USASCII` et `CHARSET:8859-1` viennent des octets cites dans l issue. Tout le reste (corps du releve, valeurs, `SECURITY:NONE`) vient du gabarit commun du corpus, pas de la source. L issue montre `SECURITY:TYPE1`, la fixture porte `SECURITY:NONE` du gabarit: ce champ n est pas la deviation.

## La deviation

L en-tete OFX 1.0.2 admet trois valeurs pour `CHARSET`: `ISO-8859-1`, `1252` et `NONE`. Le fichier de cette banque ecrit `8859-1`, sans le prefixe `ISO-`. La valeur est hors specification: ici la banque est en tort, pas le parseur qui refuse. Le piege est qu un parseur laxiste passe la chaine telle quelle a la couche de decodage: `codecs.lookup("8859-1")` echoue en Python, alors que `iso-8859-1` et `latin-1` sont des alias valides. Le rapporteur decrit exactement cela, ofxparse tentant de decoder avec un nom de codec inexistant.

Ce que dit la source:

```
ENCODING:USASCII
CHARSET:8859-1
```

## Mesure du 2026-08-05

| parseur | resultat |
|---|---|
| `ofxparse` 0.21, fichier ouvert en mode texte (usage documente) | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxparse` 0.21, fichier ouvert en binaire | 1 transaction lue, debit -10.00 du 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | echec: `OFXHeaderError: Invalid OFX header - '8859-1' is not OneOf ('ISO-8859-1', '1252', 'NONE')` |

ofxtools refuse le fichier des l en-tete, avec un message qui nomme la valeur fautive et la liste attendue: c est le comportement souhaitable. ofxparse accepte le fichier dans les deux modes et rend la transaction complete, aucun champ perdu ni tronque. Attention a ce que cette mesure dit vraiment: la fixture ne contient que des octets ASCII, donc le nom de codec `8859-1` n a jamais eu a etre reellement utilise pour decoder quoi que ce soit.

## La regle

Avant de decoder, normaliser la valeur de `CHARSET` de l en-tete: majuscules, espaces coupes, et si la valeur correspond a `^(ISO-?)?8859-1$` la remplacer par `iso-8859-1`; `1252` devient `cp1252`; `NONE` devient `ascii`. Toute autre valeur inconnue tombe sur `iso-8859-1` avec un avertissement, jamais sur une erreur de codec brute. Cette normalisation est idempotente sur un fichier conforme: `ISO-8859-1`, `1252` et `NONE` traversent la regle sans changer de sens.

## Reserve

Trois points ne sont pas etablis. La banque n est pas nommee dans l issue et le pays est inconnu, donc rien ne dit si le cas est isole ou repandu chez un emetteur donne. Seuls les deux lignes d en-tete citees plus haut viennent de la source; le corps du releve est reconstruit a partir du gabarit, l issue ne fournissant aucun octet de transaction. Surtout, la mesure ne reproduit pas le plantage decrit par le rapporteur: notre fixture est en ASCII pur, donc ofxparse 0.21 la lit sans broncher, alors que le rapport de 2019 decrit un echec de decodage. La deviation d en-tete est reelle et attestee, le plantage aval ne l est pas par cette fixture; il faudrait un octet non-ASCII dans un libelle pour le declencher, octet que la source ne fournit pas.
