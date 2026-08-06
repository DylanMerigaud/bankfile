"""Le modele normalise, MIROIR du schema JSON et jamais sa source.

`corpus/schema/transaction.schema.json` fait foi. Cette classe le suit, et
`tests/test_schema_mirror.py` echoue si les deux divergent. L'inverse (le code fait foi, le
schema le documente) condamnerait l'implementation TypeScript a courir derriere Python, et deux
implementations qui portent chacune leur verite finissent par diverger en silence.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class Transaction:
    """Une transaction, quel que soit le format d'origine.

    Le module `datetime` est importe ENTIER et non `from datetime import date`: le champ
    s'appelle `date`, donc l'import nu serait masque par lui, et les annotations suivantes
    (`booking_date: date | None`) designeraient le CHAMP au lieu du type. mypy l'a attrape,
    Python ne l'aurait jamais signale a l'execution.
    """

    date: datetime.date
    # DECIMAL, jamais float. Un centime perdu dans un binary64 est un rapprochement faux, et le
    # fichier d'origine porte deja des decimales exactes: les convertir en flottant detruit une
    # information qui etait juste.
    amount: Decimal
    currency: str
    # TOUJOURS renseigne. Les champs propres au format d'origine, tels quels. Une normalisation
    # qui jette l'original oblige a re-parser le fichier des qu'une question sort du schema, et
    # a ce moment-la plus personne n'a le fichier.
    raw: dict[str, Any]
    booking_date: datetime.date | None = None
    counterparty_name: str | None = None
    counterparty_account: str | None = None
    reference: str | None = None
    purpose: str | None = None
    bank_reference: str | None = None
    type_code: str | None = None

    def __post_init__(self) -> None:
        if len(self.currency) != 3:
            msg = f"devise ISO 4217 attendue sur 3 lettres, recu {self.currency!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Statement:
    """Un releve: un compte, une periode, des transactions."""

    account: str
    transactions: list[Transaction] = field(default_factory=list)
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    currency: str | None = None
