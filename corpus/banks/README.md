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
