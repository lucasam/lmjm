# Feature: feed-schedule-suggestions, Property 6: Unparseable Bedrock response produces error
"""Property test for unparseable Bedrock response error handling.

Validates: Requirements 8.3

When invoke_bedrock() raises an exception (simulating an unparseable or
erroneous Bedrock response), the Lambda handler must return a non-200
status code with a non-empty descriptive message.
"""

import json
import os
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.batch import Batch
from lmjm.model.feed_schedule import FeedSchedule, FeedScheduleStatus

# Ensure TABLE_NAME is set before importing the handler module,
# which reads it at module level.
os.environ.setdefault("TABLE_NAME", "test-table")

from lmjm.post_feed_schedule_suggestions import lambda_handler  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(batch_id: str = "BATCH%23test") -> dict:
    return {"pathParameters": {"batch_id": batch_id}}


def _valid_batch() -> Batch:
    return Batch(pk="BATCH#test", min_feed_stock_threshold=5000, total_animal_count=100)


def _valid_scheduled_entry() -> FeedSchedule:
    return FeedSchedule(
        pk="BATCH#test",
        sk="FEED_SCHEDULE#2025-01-10#FeedA",
        feed_type="Feed A",
        planned_date="2025-01-10",
        expected_amount_kg=10000,
        status=FeedScheduleStatus.scheduled,
    )


# ---------------------------------------------------------------------------
# Strategy: generate exception instances that invoke_bedrock might raise
# ---------------------------------------------------------------------------

_exception_strategy = st.one_of(
    # json.JSONDecodeError – malformed JSON from Bedrock
    st.tuples(
        st.text(min_size=0, max_size=100),
        st.text(min_size=0, max_size=50),
        st.integers(min_value=0, max_value=1000),
    ).map(lambda t: json.JSONDecodeError(t[0], t[1], t[2])),
    # KeyError – missing key in response body
    st.text(min_size=0, max_size=50).map(KeyError),
    # TypeError – unexpected None or wrong type
    st.text(min_size=0, max_size=100).map(TypeError),
    # ValueError – general value issues
    st.text(min_size=0, max_size=100).map(ValueError),
    # RuntimeError – catch-all unexpected errors
    st.text(min_size=0, max_size=100).map(RuntimeError),
    # Generic Exception
    st.text(min_size=0, max_size=100).map(Exception),
)


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(exc=_exception_strategy)
def test_unparseable_bedrock_response_produces_error(exc):
    """**Validates: Requirements 8.3**

    For any exception raised by invoke_bedrock (simulating an unparseable
    or erroneous Bedrock response), the handler returns a non-200 status
    code with a non-empty descriptive message.
    """
    event = _make_event()

    with (
        patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
        patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
        patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
        patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
        patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
        patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock") as mock_bedrock,
    ):
        # Set up valid DynamoDB responses so we reach the Bedrock call
        mock_batch_repo.get.return_value = _valid_batch()
        mock_fs_repo.list.return_value = [_valid_scheduled_entry()]
        mock_fcp_repo.list.return_value = []
        mock_fta_repo.list.return_value = []
        mock_fb_repo.list.return_value = []

        # invoke_bedrock raises the generated exception
        mock_bedrock.side_effect = exc

        response = lambda_handler(event, None)

    status_code = response["statusCode"]
    body = json.loads(response["body"])

    assert status_code != 200, (
        f"Expected non-200 status code when invoke_bedrock raises {type(exc).__name__}, " f"got {status_code}"
    )
    assert "message" in body, f"Response body must contain a 'message' key, got: {body}"
    assert len(body["message"]) > 0, f"Error message must be non-empty, got: {body['message']!r}"


# ---------------------------------------------------------------------------
# Unit tests for Lambda handler (Task 8.3)
# ---------------------------------------------------------------------------


class TestLambdaHandlerHappyPath:
    """Test happy path: valid batch, scheduled entries, Bedrock returns a suggestion."""

    def test_happy_path_returns_200_with_suggestions(self):
        """**Validates: Requirements 1.2, 2.1**

        Given a valid batch with scheduled entries and a Bedrock response
        containing one move suggestion, the handler returns 200 with one
        suggestion in the body.
        """
        event = _make_event()

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock") as mock_bedrock,
        ):
            mock_batch_repo.get.return_value = _valid_batch()
            mock_fs_repo.list.return_value = [_valid_scheduled_entry()]
            mock_fcp_repo.list.return_value = []
            mock_fta_repo.list.return_value = []
            mock_fb_repo.list.return_value = []
            mock_bedrock.return_value = "Move schedule from 2025-01-10 with Feed A to 2025-01-15"

            response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["suggestions"]) == 1
        suggestion = body["suggestions"][0]
        assert suggestion["planned_date"] == "2025-01-10"
        assert suggestion["feed_type"] == "Feed A"
        assert suggestion["new_planned_date"] == "2025-01-15"
        assert "1 suggestion(s) generated" in body["message"]


class TestLambdaHandlerBatchNotFound:
    """Test that a missing batch returns 404."""

    def test_batch_not_found_returns_404(self):
        """**Validates: Requirements 1.2, 8.3**"""
        event = _make_event()

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo"),
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo"),
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo"),
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo"),
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock"),
        ):
            mock_batch_repo.get.return_value = None

            response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["message"] == "Batch not found"


class TestLambdaHandlerNoScheduledEntries:
    """Test that no scheduled entries returns 200 with empty suggestions."""

    def test_no_scheduled_entries_returns_empty_suggestions(self):
        """**Validates: Requirements 2.2, 2.3**"""
        event = _make_event()

        delivered_entry = FeedSchedule(
            pk="BATCH#test",
            sk="FEED_SCHEDULE#2025-01-10#FeedA",
            feed_type="Feed A",
            planned_date="2025-01-10",
            expected_amount_kg=10000,
            status=FeedScheduleStatus.delivered,
        )

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock"),
        ):
            mock_batch_repo.get.return_value = _valid_batch()
            mock_fs_repo.list.return_value = [delivered_entry]
            mock_fcp_repo.list.return_value = []
            mock_fta_repo.list.return_value = []
            mock_fb_repo.list.return_value = []

            response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["suggestions"] == []
        assert body["message"] == "No scheduled deliveries to optimize"


class TestLambdaHandlerBedrockTimeout:
    """Test that a Bedrock timeout returns 504."""

    def test_bedrock_timeout_returns_504(self):
        """**Validates: Requirements 8.4**"""
        from botocore.exceptions import ReadTimeoutError

        event = _make_event()

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock") as mock_bedrock,
        ):
            mock_batch_repo.get.return_value = _valid_batch()
            mock_fs_repo.list.return_value = [_valid_scheduled_entry()]
            mock_fcp_repo.list.return_value = []
            mock_fta_repo.list.return_value = []
            mock_fb_repo.list.return_value = []
            mock_bedrock.side_effect = ReadTimeoutError(endpoint_url="https://bedrock.us-east-1.amazonaws.com")

            response = lambda_handler(event, None)

        assert response["statusCode"] == 504
        body = json.loads(response["body"])
        assert body["message"] == "AI service timed out"


class TestLambdaHandlerBedrockServiceError:
    """Test that a Bedrock ClientError returns 502."""

    def test_bedrock_client_error_returns_502(self):
        """**Validates: Requirements 8.3**"""
        from botocore.exceptions import ClientError

        event = _make_event()

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock") as mock_bedrock,
        ):
            mock_batch_repo.get.return_value = _valid_batch()
            mock_fs_repo.list.return_value = [_valid_scheduled_entry()]
            mock_fcp_repo.list.return_value = []
            mock_fta_repo.list.return_value = []
            mock_fb_repo.list.return_value = []
            mock_bedrock.side_effect = ClientError(
                error_response={
                    "Error": {
                        "Code": "ThrottlingException",
                        "Message": "Rate exceeded",
                    }
                },
                operation_name="InvokeModel",
            )

            response = lambda_handler(event, None)

        assert response["statusCode"] == 502
        body = json.loads(response["body"])
        assert "AI service error" in body["message"]


class TestLambdaHandlerUnparseableResponse:
    """Test that a generic Bedrock exception returns 500."""

    def test_unparseable_bedrock_response_returns_500(self):
        """**Validates: Requirements 8.3**"""
        event = _make_event()

        with (
            patch("lmjm.post_feed_schedule_suggestions.batch_repo") as mock_batch_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_schedule_repo") as mock_fs_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_consumption_plan_repo") as mock_fcp_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_truck_arrival_repo") as mock_fta_repo,
            patch("lmjm.post_feed_schedule_suggestions.feed_balance_repo") as mock_fb_repo,
            patch("lmjm.post_feed_schedule_suggestions.invoke_bedrock") as mock_bedrock,
        ):
            mock_batch_repo.get.return_value = _valid_batch()
            mock_fs_repo.list.return_value = [_valid_scheduled_entry()]
            mock_fcp_repo.list.return_value = []
            mock_fta_repo.list.return_value = []
            mock_fb_repo.list.return_value = []
            mock_bedrock.side_effect = Exception("Unexpected error")

            response = lambda_handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["message"] == "Could not parse AI suggestions"
