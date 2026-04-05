"""Property-based tests for batch identification via supply_id.

Property 9: Batch identification via supply_id

For any parsed NF-e with an xPed (order number) value, and a set of Batches:
if exactly one Batch has a supply_id matching the xPed value, the FiscalDocument
pk should be that Batch's pk. If no Batch matches, the FiscalDocument pk should
be "UNMATCHED_FISCAL".

**Validates: Requirements 6.2, 6.3**
"""

from typing import Optional

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model import Batch
from lmjm.process_fiscal_email import _find_batch_by_supply_id

# --- Strategies ---

supply_id_st = st.integers(min_value=1, max_value=999_999_999)

batch_pk_st = st.uuids().map(str)


def _make_batch(pk: str, supply_id: int) -> Batch:
    return Batch(pk=pk, sk="Batch", supply_id=supply_id)


def _oracle(order_number: str, batches: list[Batch]) -> Optional[Batch]:
    """Reference implementation: linear scan matching str(supply_id) == order_number."""
    for batch in batches:
        if str(batch.supply_id) == order_number:
            return batch
    return None


# --- Property Tests ---


@given(
    supply_id=supply_id_st,
    pk=batch_pk_st,
)
@settings(max_examples=100)
def test_single_matching_batch_returns_that_batch(
    supply_id: int,
    pk: str,
) -> None:
    """Batch with matching supply_id → returns that batch.

    **Validates: Requirements 6.2, 6.3**
    """
    batch = _make_batch(pk=pk, supply_id=supply_id)
    batches = [batch]

    result = _find_batch_by_supply_id(str(supply_id), batches)

    assert result is not None
    assert result.pk == pk
    assert result.supply_id == supply_id


@given(
    order_number_id=supply_id_st,
    other_ids=st.lists(supply_id_st, min_size=1, max_size=10),
    pks=st.lists(batch_pk_st, min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_no_matching_batch_returns_none(
    order_number_id: int,
    other_ids: list[int],
    pks: list[str],
) -> None:
    """No batch with matching supply_id → returns None.

    **Validates: Requirements 6.2, 6.3**
    """
    # Ensure none of the other_ids match order_number_id
    filtered = [(sid, pk) for sid, pk in zip(other_ids, pks) if sid != order_number_id]
    batches = [_make_batch(pk=pk, supply_id=sid) for sid, pk in filtered]

    result = _find_batch_by_supply_id(str(order_number_id), batches)

    assert result is None


@given(
    supply_id=supply_id_st,
    target_pk=batch_pk_st,
    other_ids=st.lists(supply_id_st, min_size=1, max_size=10),
    other_pks=st.lists(batch_pk_st, min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_multiple_batches_only_one_matches(
    supply_id: int,
    target_pk: str,
    other_ids: list[int],
    other_pks: list[str],
) -> None:
    """Multiple batches, only one matches → returns the matching one.

    **Validates: Requirements 6.2, 6.3**
    """
    # Build non-matching batches
    non_matching = [
        _make_batch(pk=pk, supply_id=sid)
        for sid, pk in zip(other_ids, other_pks)
        if sid != supply_id
    ]

    # Insert the matching batch
    matching = _make_batch(pk=target_pk, supply_id=supply_id)
    batches = non_matching + [matching]

    result = _find_batch_by_supply_id(str(supply_id), batches)

    assert result is not None
    assert result.pk == target_pk
    assert result.supply_id == supply_id


@given(
    supply_id=supply_id_st,
    batches_data=st.lists(
        st.tuples(supply_id_st, batch_pk_st),
        min_size=0,
        max_size=10,
    ),
)
@settings(max_examples=200)
def test_general_batch_identification_agrees_with_oracle(
    supply_id: int,
    batches_data: list[tuple[int, str]],
) -> None:
    """General property: _find_batch_by_supply_id agrees with the oracle.

    **Validates: Requirements 6.2, 6.3**
    """
    batches = [_make_batch(pk=pk, supply_id=sid) for sid, pk in batches_data]
    order_number = str(supply_id)

    result = _find_batch_by_supply_id(order_number, batches)
    expected = _oracle(order_number, batches)

    assert result == expected
