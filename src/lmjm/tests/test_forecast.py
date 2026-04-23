# Feature: feed-schedule-suggestions, Task 3.2: Unit tests for projected balance calculation
"""Unit tests for compute_projected_balances.

Validates: Requirements 2.1
"""

from decimal import Decimal

from lmjm.model.feed_balance import FeedBalance
from lmjm.model.feed_consumption_plan import FeedConsumptionPlan
from lmjm.model.feed_schedule import FeedSchedule
from lmjm.model.feed_schedule_suggestion import DailyBalance
from lmjm.model.feed_truck_arrival import FeedTruckArrival
from lmjm.suggestion_engine.forecast import compute_projected_balances


class TestEmptyConsumptionPlan:
    """An empty consumption plan should produce no daily balances."""

    def test_empty_consumption_plan_returns_empty_list(self):
        result = compute_projected_balances(
            consumption_plan=[],
            scheduled_entries=[],
            truck_arrivals=[],
            balances=[],
            total_animal_count=100,
        )
        assert result == []


class TestSingleDayConsumptionOnly:
    """Single day with only consumption — balance decreases from zero."""

    def test_balance_decreases_by_consumption(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("2.5"),
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=[],
            truck_arrivals=[],
            balances=[],
            total_animal_count=100,
        )

        assert len(result) == 1
        day = result[0]
        assert day.date == "2025-01-01"
        # consumption = int(2.5 * 100) = 250
        assert day.consumption_kg == 250
        assert day.scheduled_delivery_kg == 0
        assert day.arrival_kg == 0
        # projected = 0 - 250 + 0 + 0 = -250
        assert day.projected_balance_kg == -250


class TestSingleDayWithDelivery:
    """Single day with consumption and a scheduled delivery."""

    def test_delivery_offsets_consumption(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("2.0"),
            ),
        ]
        deliveries = [
            FeedSchedule(
                pk="BATCH#1",
                sk="FS#1",
                planned_date="2025-01-01",
                expected_amount_kg=5000,
                status="scheduled",
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=deliveries,
            truck_arrivals=[],
            balances=[],
            total_animal_count=100,
        )

        assert len(result) == 1
        day = result[0]
        # consumption = int(2.0 * 100) = 200
        assert day.consumption_kg == 200
        assert day.scheduled_delivery_kg == 5000
        # projected = 0 - 200 + 5000 = 4800
        assert day.projected_balance_kg == 4800


class TestMultipleDaysCumulativeBalance:
    """Multiple days showing cumulative balance changes."""

    def test_balance_carries_forward(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("1.0"),
            ),
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#2",
                date="2025-01-02",
                expected_kg_per_animal=Decimal("1.0"),
            ),
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#3",
                date="2025-01-03",
                expected_kg_per_animal=Decimal("1.0"),
            ),
        ]
        deliveries = [
            FeedSchedule(
                pk="BATCH#1",
                sk="FS#1",
                planned_date="2025-01-01",
                expected_amount_kg=1000,
                status="scheduled",
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=deliveries,
            truck_arrivals=[],
            balances=[],
            total_animal_count=50,
        )

        assert len(result) == 3
        # Day 1: 0 - 50 + 1000 = 950
        assert result[0].date == "2025-01-01"
        assert result[0].consumption_kg == 50
        assert result[0].projected_balance_kg == 950
        # Day 2: 950 - 50 = 900
        assert result[1].date == "2025-01-02"
        assert result[1].consumption_kg == 50
        assert result[1].projected_balance_kg == 900
        # Day 3: 900 - 50 = 850
        assert result[2].date == "2025-01-03"
        assert result[2].consumption_kg == 50
        assert result[2].projected_balance_kg == 850


class TestBalanceMeasurementResetsProjection:
    """A balance measurement resets the projected balance on that date."""

    def test_measurement_overrides_calculated_balance(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("1.0"),
            ),
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#2",
                date="2025-01-02",
                expected_kg_per_animal=Decimal("1.0"),
            ),
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#3",
                date="2025-01-03",
                expected_kg_per_animal=Decimal("1.0"),
            ),
        ]
        deliveries = [
            FeedSchedule(
                pk="BATCH#1",
                sk="FS#1",
                planned_date="2025-01-01",
                expected_amount_kg=1000,
                status="scheduled",
            ),
        ]
        balances = [
            FeedBalance(
                pk="BATCH#1",
                sk="BAL#1",
                measurement_date="2025-01-02",
                balance_kg=500,
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=deliveries,
            truck_arrivals=[],
            balances=balances,
            total_animal_count=50,
        )

        assert len(result) == 3
        # Day 1: initial_balance=500 (latest measurement) - 50 + 1000 = 1450
        assert result[0].projected_balance_kg == 1450
        # Day 2: would be 1450 - 50 = 1400, but measurement resets to 500
        assert result[1].projected_balance_kg == 500
        # Day 3: 500 - 50 = 450
        assert result[2].projected_balance_kg == 450


class TestMultipleDeliveriesSameDate:
    """Multiple scheduled deliveries on the same date are summed."""

    def test_deliveries_summed_on_same_date(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("1.0"),
            ),
        ]
        deliveries = [
            FeedSchedule(
                pk="BATCH#1",
                sk="FS#1",
                planned_date="2025-01-01",
                expected_amount_kg=3000,
                status="scheduled",
            ),
            FeedSchedule(
                pk="BATCH#1",
                sk="FS#2",
                planned_date="2025-01-01",
                expected_amount_kg=2000,
                status="scheduled",
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=deliveries,
            truck_arrivals=[],
            balances=[],
            total_animal_count=100,
        )

        assert len(result) == 1
        # Both deliveries summed: 3000 + 2000 = 5000
        assert result[0].scheduled_delivery_kg == 5000
        # projected = 0 - 100 + 5000 = 4900
        assert result[0].projected_balance_kg == 4900


class TestMultipleTruckArrivalsSameDate:
    """Multiple truck arrivals on the same date are summed."""

    def test_arrivals_summed_on_same_date(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-01",
                expected_kg_per_animal=Decimal("1.0"),
            ),
        ]
        arrivals = [
            FeedTruckArrival(
                pk="BATCH#1",
                sk="TA#1",
                receive_date="2025-01-01",
                actual_amount_kg=4000,
            ),
            FeedTruckArrival(
                pk="BATCH#1",
                sk="TA#2",
                receive_date="2025-01-01",
                actual_amount_kg=1500,
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=[],
            truck_arrivals=arrivals,
            balances=[],
            total_animal_count=100,
        )

        assert len(result) == 1
        # Both arrivals summed: 4000 + 1500 = 5500
        assert result[0].arrival_kg == 5500
        # projected = 0 - 100 + 5500 = 5400
        assert result[0].projected_balance_kg == 5400


class TestInitialBalanceFromLatestMeasurement:
    """Initial balance comes from the latest balance measurement."""

    def test_latest_measurement_used_as_initial_balance(self):
        plan = [
            FeedConsumptionPlan(
                pk="BATCH#1",
                sk="CP#1",
                date="2025-01-05",
                expected_kg_per_animal=Decimal("2.0"),
            ),
        ]
        balances = [
            FeedBalance(
                pk="BATCH#1",
                sk="BAL#1",
                measurement_date="2025-01-01",
                balance_kg=1000,
            ),
            FeedBalance(
                pk="BATCH#1",
                sk="BAL#2",
                measurement_date="2025-01-03",
                balance_kg=3000,
            ),
            FeedBalance(
                pk="BATCH#1",
                sk="BAL#3",
                measurement_date="2025-01-02",
                balance_kg=2000,
            ),
        ]

        result = compute_projected_balances(
            consumption_plan=plan,
            scheduled_entries=[],
            truck_arrivals=[],
            balances=balances,
            total_animal_count=100,
        )

        assert len(result) == 1
        # Latest measurement is 2025-01-03 with balance_kg=3000
        # consumption = int(2.0 * 100) = 200
        # projected = 3000 - 200 = 2800
        assert result[0].projected_balance_kg == 2800
