"""Deltas keep unrelated original hard constraints."""

from app.decision.intent.models import ConstraintField
from app.decision.negotiation.delta import apply_working_intent, delta_from_turn
from app.decision.negotiation.interpreter import RuleBasedNegotiationInterpreter
from app.decision.negotiation.models import BuyerTurnInput
from tests.offer_fixtures import travel_intent

INTERP = RuleBasedNegotiationInterpreter()


def test_price_counter_does_not_drop_anc() -> None:
    original = travel_intent()
    turn = INTERP.interpret(BuyerTurnInput(message="Can you get below A$315?"))
    delta = delta_from_turn(turn)
    working = apply_working_intent(original, [delta])
    fields = {item.field for item in working.hard_constraints}
    assert ConstraintField.ANC in fields
    assert ConstraintField.DELIVERY_DAYS in fields or (
        ConstraintField.SAME_DAY_DELIVERY in fields
    )


def test_relax_same_day_is_explicit() -> None:
    original = travel_intent()
    turn = INTERP.interpret(
        BuyerTurnInput(message="I don't need it today, standard delivery is fine")
    )
    working = apply_working_intent(original, [delta_from_turn(turn)])
    fields = {item.field for item in working.hard_constraints}
    assert ConstraintField.SAME_DAY_DELIVERY not in fields
    assert ConstraintField.ANC in fields


def test_foldable_requires_rematch() -> None:
    turn = INTERP.interpret(BuyerTurnInput(message="I need a foldable model"))
    delta = delta_from_turn(turn)
    assert delta.rematch_required is True
    assert delta.foldable_required is True
