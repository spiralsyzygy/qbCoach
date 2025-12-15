from qb_engine.card_hydrator import CardHydrator
from qb_engine.projection import compute_projection_targets


def test_grasslands_wolf_projection_varies_by_lane():
    hydrator = CardHydrator()
    card = hydrator.get_card("008")  # Grasslands Wolf: B3P, C2P

    top_targets = set(compute_projection_targets(0, 0, card).targets)
    mid_targets = set(compute_projection_targets(1, 0, card).targets)
    bot_targets = set(compute_projection_targets(2, 0, card).targets)

    # Ensure projections differ across lanes (top loses above, bot loses below).
    assert top_targets != mid_targets or mid_targets != bot_targets
