"""Property-based tests for FeedConsumptionTemplate.

Feature: feed-consumption-template
"""

import importlib
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import combinations
from typing import Any

import boto3
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model.batch import Batch
from lmjm.model.feed_consumption_template import FeedConsumptionTemplate
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

# --- Strategies ---

sequence_st = st.integers(min_value=0, max_value=10_000)
expected_piglet_weight_st = st.integers(min_value=0, max_value=100_000)
expected_kg_per_animal_st = st.decimals(
    min_value=0,
    max_value=1000,
    allow_nan=False,
    allow_infinity=False,
    places=3,
)

REQUIRED_FIELDS = ["sequence", "expected_piglet_weight", "expected_kg_per_animal"]

# All non-empty subsets of required fields to omit (1, 2, or 3 fields missing)
_fields_to_omit_options: list[tuple[str, ...]] = []
for r in range(1, len(REQUIRED_FIELDS) + 1):
    _fields_to_omit_options.extend(combinations(REQUIRED_FIELDS, r))

fields_to_omit_st = st.sampled_from(_fields_to_omit_options)


# --- Property Tests ---


# Feature: feed-consumption-template, Property 1: FeedConsumptionTemplate serialization round-trip
@given(
    sequence=sequence_st,
    expected_piglet_weight=expected_piglet_weight_st,
    expected_kg_per_animal=expected_kg_per_animal_st,
)
@settings(max_examples=100)
def test_feed_consumption_template_round_trip(
    sequence: int,
    expected_piglet_weight: int,
    expected_kg_per_animal: Decimal,
) -> None:
    """Property 1: FeedConsumptionTemplate serialization round-trip.

    For any valid FeedConsumptionTemplate instance with arbitrary sequence (>= 0),
    expected_piglet_weight (>= 0), and expected_kg_per_animal (>= 0), serializing
    to a dictionary via serialize_to_dict and then deserializing back via
    load_data_class_from_dict should produce an equivalent object with identical
    field values.

    **Validates: Requirements 1.3, 1.4, 1.5**
    """
    original = FeedConsumptionTemplate(
        pk="FEED_CONSUMPTION_TEMPLATE",
        sk=f"FeedConsumptionTemplate|{sequence}",
        sequence=sequence,
        expected_piglet_weight=expected_piglet_weight,
        expected_kg_per_animal=expected_kg_per_animal,
    )

    serialized = serialize_to_dict(original)
    restored = load_data_class_from_dict(serialized, FeedConsumptionTemplate)

    assert restored.pk == original.pk
    assert restored.sk == original.sk
    assert restored.sequence == original.sequence
    assert restored.expected_piglet_weight == original.expected_piglet_weight
    assert restored.expected_kg_per_animal == original.expected_kg_per_animal
    assert restored == original


# --- Helpers for Property 2+ (POST handler tests with moto) ---


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    return dynamodb.create_table(
        TableName="lmjm",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _post_event(body: dict[str, Any]) -> dict[str, Any]:
    return {"body": json.dumps(body)}


# Feature: feed-consumption-template, Property 2: POST validation rejects incomplete payloads
@mock_aws
def test_post_template_rejects_missing_fields() -> None:
    """Property 2: POST validation rejects incomplete payloads.

    For any subset of the required fields {sequence, expected_piglet_weight,
    expected_kg_per_animal} where at least one field is missing, the POST handler
    shall return HTTP status 400 with an error message listing the missing fields.

    **Validates: Requirements 2.3**
    """
    os.environ["TABLE_NAME"] = "lmjm"
    _create_table()

    import lmjm.post_feed_consumption_template as mod

    importlib.reload(mod)

    @given(
        fields_to_omit=fields_to_omit_st,
        sequence=sequence_st,
        expected_piglet_weight=expected_piglet_weight_st,
        expected_kg_per_animal=expected_kg_per_animal_st,
    )
    @settings(max_examples=100, deadline=None)
    def run_property(
        fields_to_omit: tuple[str, ...],
        sequence: int,
        expected_piglet_weight: int,
        expected_kg_per_animal: Decimal,
    ) -> None:
        # Build a complete payload, then remove the fields to omit
        full_payload: dict[str, Any] = {
            "sequence": sequence,
            "expected_piglet_weight": expected_piglet_weight,
            "expected_kg_per_animal": float(expected_kg_per_animal),
        }
        incomplete_payload = {k: v for k, v in full_payload.items() if k not in fields_to_omit}

        result = mod.lambda_handler(_post_event(incomplete_payload), None)

        assert result["statusCode"] == 400

        body = json.loads(result["body"])
        error_message = body["message"]

        # Every omitted field must appear in the error message
        for field in fields_to_omit:
            assert field in error_message, f"Expected '{field}' in error message: {error_message}"

    run_property()


# Feature: feed-consumption-template, Property 3: POST with valid fields creates correct record
@mock_aws
def test_post_template_valid_fields_creates_record() -> None:
    """Property 3: POST with valid fields creates correct record.

    For any valid combination of sequence (>= 0), expected_piglet_weight (>= 0),
    and expected_kg_per_animal (>= 0), the POST handler shall return HTTP status 201
    and the saved record shall have pk="FEED_CONSUMPTION_TEMPLATE" and
    sk="FeedConsumptionTemplate|{sequence}".

    **Validates: Requirements 2.2**
    """
    os.environ["TABLE_NAME"] = "lmjm"
    _create_table()

    import lmjm.post_feed_consumption_template as mod

    importlib.reload(mod)

    @given(
        sequence=sequence_st,
        expected_piglet_weight=expected_piglet_weight_st,
        expected_kg_per_animal=expected_kg_per_animal_st,
    )
    @settings(max_examples=100, deadline=None)
    def run_property(
        sequence: int,
        expected_piglet_weight: int,
        expected_kg_per_animal: Decimal,
    ) -> None:
        payload: dict[str, Any] = {
            "sequence": sequence,
            "expected_piglet_weight": expected_piglet_weight,
            "expected_kg_per_animal": float(expected_kg_per_animal),
        }

        result = mod.lambda_handler(_post_event(payload), None)

        assert result["statusCode"] == 201

        body = json.loads(result["body"])
        assert body["pk"] == "FEED_CONSUMPTION_TEMPLATE"
        assert body["sk"] == f"FeedConsumptionTemplate|{sequence}"
        assert body["sequence"] == sequence
        assert body["expected_piglet_weight"] == expected_piglet_weight

    run_property()


# --- Helpers for Property 4 (plan generation) ---


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super().default(o)


def _decimal_safe_serialize(obj: object) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = serialize_to_dict(obj)
    return json.loads(json.dumps(d, cls=_DecimalEncoder), parse_float=Decimal)  # type: ignore[no-any-return]


def _generate_event(batch_id: str) -> dict[str, Any]:
    return {"pathParameters": {"batch_id": batch_id}}


# --- Strategies for Property 4 ---

# Dates between 2020-01-01 and 2030-12-31
date_st = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2030, 12, 31).date(),
).map(lambda d: d.strftime("%Y-%m-%d"))

# initial_animal_weight as a positive integer (Decimal in the model, but compared as int)
initial_weight_st = st.integers(min_value=1, max_value=50_000)


@st.composite
def templates_with_match_st(draw: st.DrawFn, initial_weight: int) -> list[FeedConsumptionTemplate]:
    """Generate a non-empty list of templates where at least one has
    expected_piglet_weight >= initial_weight.

    Templates are returned sorted by sk (lexicographic), which matches
    the DynamoDB ScanIndexForward=True ordering used by the handler.
    """
    # Generate 1-20 template entries
    n = draw(st.integers(min_value=1, max_value=20))

    # Generate unique sequences
    sequences = sorted(draw(st.lists(st.integers(min_value=0, max_value=10_000), min_size=n, max_size=n, unique=True)))

    # Generate piglet weights for each entry
    piglet_weights = [draw(st.integers(min_value=0, max_value=100_000)) for _ in range(n)]

    # Ensure at least one entry has expected_piglet_weight >= initial_weight
    # Pick a random index and force it
    force_idx = draw(st.integers(min_value=0, max_value=n - 1))
    piglet_weights[force_idx] = draw(st.integers(min_value=initial_weight, max_value=100_000))

    templates: list[FeedConsumptionTemplate] = []
    for i in range(n):
        kg = draw(expected_kg_per_animal_st)
        templates.append(
            FeedConsumptionTemplate(
                pk="FEED_CONSUMPTION_TEMPLATE",
                sk=f"FeedConsumptionTemplate|{sequences[i]}",
                sequence=sequences[i],
                expected_piglet_weight=piglet_weights[i],
                expected_kg_per_animal=kg,
            )
        )

    # Sort by sk (lexicographic) to match DynamoDB ScanIndexForward=True ordering
    templates.sort(key=lambda t: t.sk)
    return templates


# Feature: feed-consumption-template, Property 4: Plan generation produces correct day numbering and dates
@mock_aws
def test_generate_plan_correctness() -> None:
    """Property 4: Plan generation produces correct day numbering and dates from template.

    For any batch with a valid average_start_date and initial_animal_weight, and for any
    non-empty list of FeedConsumptionTemplate entries sorted by sequence where at least one
    entry has expected_piglet_weight >= initial_animal_weight, the generated FeedConsumptionPlan
    entries shall satisfy:
    1. The first plan entry corresponds to the first template entry where
       expected_piglet_weight >= initial_animal_weight
    2. The first plan entry has day_number = 1 and date = average_start_date + 1 day
    3. Each subsequent plan entry has day_number incremented by 1 and date incremented by 1 day
    4. Each plan entry's expected_kg_per_animal and expected_piglet_weight match the
       corresponding template entry

    **Validates: Requirements 4.2, 4.3, 4.8**
    """
    os.environ["TABLE_NAME"] = "lmjm"
    table = _create_table()

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    # Patch the repo serializers for moto Decimal compatibility
    import lmjm.repo.feed_consumption_template_repo as tmpl_repo_mod
    import lmjm.repo.feed_consumption_plan_repo as plan_repo_mod
    import lmjm.repo.batch_repo as batch_repo_mod

    original_tmpl_serialize = tmpl_repo_mod.serialize_to_dict
    original_plan_serialize = plan_repo_mod.serialize_to_dict
    original_batch_serialize = batch_repo_mod.serialize_to_dict
    tmpl_repo_mod.serialize_to_dict = _decimal_safe_serialize
    plan_repo_mod.serialize_to_dict = _decimal_safe_serialize
    batch_repo_mod.serialize_to_dict = _decimal_safe_serialize

    try:

        @given(
            avg_start_date=date_st,
            initial_weight=initial_weight_st,
            data=st.data(),
        )
        @settings(max_examples=100, deadline=None)
        def run_property(avg_start_date: str, initial_weight: int, data: st.DataObject) -> None:
            templates = data.draw(templates_with_match_st(initial_weight))

            batch_id = "test-batch"

            # Clean up previous run data
            _clear_table(table)

            # Seed batch
            batch = Batch(
                pk=batch_id,
                sk="Batch",
                average_start_date=avg_start_date,
                initial_animal_weight=Decimal(initial_weight),
            )
            table.put_item(Item=_decimal_safe_serialize(batch))

            # Seed templates
            for t in templates:
                table.put_item(Item=_decimal_safe_serialize(t))

            # Invoke handler
            result = mod.lambda_handler(_generate_event(batch_id), None)

            assert result["statusCode"] == 200, f"Expected 200, got {result['statusCode']}: {result['body']}"

            body = json.loads(result["body"])

            # Find the expected start index: first template where expected_piglet_weight >= initial_weight
            start_index: int | None = None
            for i, t in enumerate(templates):
                if t.expected_piglet_weight >= initial_weight:
                    start_index = i
                    break

            assert start_index is not None, "Should have found a matching template"

            expected_templates = templates[start_index:]
            assert len(body) == len(expected_templates), (
                f"Expected {len(expected_templates)} plan entries, got {len(body)}"
            )

            base_date = datetime.strptime(avg_start_date, "%Y-%m-%d")

            for j, (plan_entry, tmpl) in enumerate(zip(body, expected_templates)):
                expected_day = j + 1
                expected_date = (base_date + timedelta(days=expected_day)).strftime("%Y-%m-%d")

                # Verify day_number starts at 1 and increments by 1
                assert plan_entry["day_number"] == expected_day, (
                    f"Entry {j}: expected day_number={expected_day}, got {plan_entry['day_number']}"
                )

                # Verify date = average_start_date + day_number days
                assert plan_entry["date"] == expected_date, (
                    f"Entry {j}: expected date={expected_date}, got {plan_entry['date']}"
                )

                # Verify expected_piglet_weight matches template
                assert plan_entry["expected_piglet_weight"] == tmpl.expected_piglet_weight, (
                    f"Entry {j}: expected_piglet_weight mismatch: "
                    f"{plan_entry['expected_piglet_weight']} != {tmpl.expected_piglet_weight}"
                )

                # Verify expected_kg_per_animal matches template
                # The response serializes Decimal to float, so compare as float
                assert float(plan_entry["expected_kg_per_animal"]) == pytest.approx(
                    float(tmpl.expected_kg_per_animal), abs=1e-6
                ), (
                    f"Entry {j}: expected_kg_per_animal mismatch: "
                    f"{plan_entry['expected_kg_per_animal']} != {tmpl.expected_kg_per_animal}"
                )

        run_property()

    finally:
        tmpl_repo_mod.serialize_to_dict = original_tmpl_serialize
        plan_repo_mod.serialize_to_dict = original_plan_serialize
        batch_repo_mod.serialize_to_dict = original_batch_serialize


def _clear_table(table: Any) -> None:
    """Remove all items from the moto DynamoDB table."""
    response = table.scan(ProjectionExpression="pk, sk")
    with table.batch_writer() as batch:
        for item in response["Items"]:
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
