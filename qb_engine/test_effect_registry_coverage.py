from pathlib import Path

from qb_engine.effect_registry_utils import get_all_effect_ids_from_db, load_effect_registry
from qb_engine.effect_engine import EffectOp


KNOWN_OP_TYPES = {
    "modify_power",
    "modify_power_scale",
    "destroy_cards",
    "replace_ally",
    "add_to_hand",
    "spawn_token",
    "modify_tile_ranks",
    "score_bonus",
    "expand_positions",
}


def test_db_effect_ids_exist_in_registry():
    registry = load_effect_registry()
    effect_ids, _rows = get_all_effect_ids_from_db()

    missing = sorted(e for e in effect_ids if e not in registry)
    assert not missing, f"Effect IDs missing from registry: {missing}"


def test_registry_ops_are_known():
    registry = load_effect_registry()
    unknown = []
    for eid, entry in registry.items():
        for op in entry.get("operations", []):
            op_type = op.get("type")
            if op_type not in KNOWN_OP_TYPES:
                unknown.append((eid, op_type))
    assert not unknown, f"Unknown op types in registry: {unknown}"


def test_effect_op_dataclass_accepts_known_fields():
    # Ensure EffectOp can be constructed from registry entries without missing keys.
    registry = load_effect_registry()
    for entry in registry.values():
        for op in entry.get("operations", []):
            EffectOp(
                type=op.get("type"),
                stat=op.get("stat"),
                amount=op.get("amount"),
                apply_to=op.get("apply_to"),
                per=op.get("per"),
                amount_per=op.get("amount_per"),
                card_ids=op.get("card_ids"),
                adjustment=op.get("adjustment"),
                mode=op.get("mode"),
                conditions=op.get("conditions"),
                raw=op,
            )

