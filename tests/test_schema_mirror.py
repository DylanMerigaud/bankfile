"""Le modele Python et le schema JSON ne doivent pas diverger.

Le schema fait foi: il sert aussi l'implementation TypeScript a venir. Sans ce test, le code
Python devient la reference de fait, la version TS court derriere, et les deux portent chacune
leur verite. C'est ainsi qu'un projet multi-langage meurt, et c'est previsible, donc garde.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import fields
from pathlib import Path

from bankstatements.model import Transaction

SCHEMA = Path(__file__).resolve().parent.parent / "corpus" / "schema" / "transaction.schema.json"


def test_les_champs_du_schema_et_du_modele_sont_les_memes() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    attendus = set(schema["properties"])
    presents = {f.name for f in fields(Transaction)}
    assert presents == attendus, (
        f"manquants dans le modele: {sorted(attendus - presents)}; "
        f"absents du schema: {sorted(presents - attendus)}"
    )


def test_les_champs_obligatoires_du_schema_n_ont_pas_de_defaut() -> None:
    """Un champ requis par le schema mais optionnel dans le modele laisse construire un objet
    invalide sans que rien ne le dise."""
    requis = set(json.loads(SCHEMA.read_text(encoding="utf-8"))["required"])
    for f in fields(Transaction):
        if f.name in requis:
            assert f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING, (
                f"{f.name} est requis par le schema mais porte un defaut dans le modele"
            )


def test_le_schema_refuse_les_champs_inconnus() -> None:
    """`additionalProperties: false` est ce qui rend le miroir verifiable des deux cotes."""
    assert json.loads(SCHEMA.read_text(encoding="utf-8"))["additionalProperties"] is False
