# Contribuer

## Ce qui aide le plus

Un extrait anonymise d'un fichier que la librairie lit mal. C'est ce qui construit l'actif du
projet, et c'est la seule chose qu'aucun modele ne peut produire a votre place: la
specification est publique, la facon dont votre banque s'en ecarte ne l'est pas.

**Anonymisez toujours**: remplacez montants, noms et numeros de compte. La structure est ce qui
compte, jamais le contenu.

## Une correction de parsing sans fixture reviendra

Toute correction porte son fichier sous `corpus/banks/`, avec le `.md` qui dit la banque, le
format et la deviation. Sinon la regression revient au premier refactor, et le corpus, qui est
l'actif, n'a pas grandi.

## Avant d'ouvrir une PR

```bash
uv sync --all-groups
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

Le lint est strict et ses exemptions sont ecrites dans `pyproject.toml` avec leur raison. En
ajouter une sans raison n'est pas une exemption, c'est une regle qu'on eteint parce qu'elle
derange.
