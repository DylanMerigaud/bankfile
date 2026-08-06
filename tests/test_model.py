"""Les invariants du modele, ceux dont la violation produit un resultat FAUX et non une erreur."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from bankfile.model import Transaction


def tx(**kw: object) -> Transaction:
    base: dict[str, object] = {
        "date": datetime.date(2026, 1, 15),
        "amount": Decimal("-42.17"),
        "currency": "EUR",
        "raw": {},
    }
    base.update(kw)
    return Transaction(**base)  # type: ignore[arg-type]


def test_le_montant_reste_exact() -> None:
    """Le piege que ce projet doit eviter: 0.1 + 0.2 en flottant ne fait pas 0.3, et un
    rapprochement bancaire faux de un centime est un rapprochement faux."""
    total = tx(amount=Decimal("0.1")).amount + tx(amount=Decimal("0.2")).amount
    assert total == Decimal("0.3")
    # Le meme calcul en binary64, pour que la raison du Decimal soit visible et non affirmee.
    en_flottant = 0.1 + 0.2
    assert en_flottant != 0.3
    assert Decimal(str(en_flottant)) != Decimal("0.3")


def test_une_devise_mal_formee_est_refusee_a_la_construction() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        tx(currency="EURO")


def test_la_transaction_est_immuable() -> None:
    """Un objet de releve qui se modifie apres coup rend le rapprochement inauditable."""
    t = tx()
    with pytest.raises(AttributeError):
        t.amount = Decimal("0")  # type: ignore[misc]
