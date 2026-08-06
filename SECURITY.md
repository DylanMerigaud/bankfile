# Securite

## Signaler

Ouvrez un avis de securite prive via l'onglet Security de ce depot. Pas d'issue publique.

## Ce qui compte particulierement ici

Ce projet lit des fichiers bancaires. Deux categories priment:

**Une fuite de donnees dans le depot.** Un fichier de corpus insuffisamment anonymise est une
faille, meme s'il n'y a pas de bug. Signalez-le comme telle.

**Un parseur qui rend un montant faux sans erreur.** En finance, un resultat faux mais plausible
est pire qu'un plantage: il entre dans un rapprochement et personne ne le voit. Un ecart
silencieux entre le fichier et la sortie est traite comme une faille, pas comme un bug.
