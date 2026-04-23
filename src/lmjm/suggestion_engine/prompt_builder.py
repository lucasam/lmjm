"""Prompt builder for feed schedule suggestions.

Pure function that converts a SuggestionContext into a structured text prompt
for Amazon Bedrock, including all business rules and output format instructions.
"""

from datetime import date

from lmjm.model.feed_schedule_suggestion import SuggestionContext

_WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def build_prompt(context: SuggestionContext) -> str:
    """Build a structured prompt for the AI model from the suggestion context.

    The prompt includes:
    - Daily projected balances table
    - Scheduled deliveries (date, feed type, quantity)
    - Business rules (thresholds, grouping/ordering, weekday constraints)
    - Output format instructions

    This is a pure function with no side effects.
    """
    sections = [
        _build_system_section(),
        _build_balances_section(context),
        _build_deliveries_section(context),
        _build_rules_section(context),
        _build_strategy_section(),
        _build_output_section(),
    ]
    return "\n\n".join(sections)


def _build_system_section() -> str:
    today = date.today().isoformat()
    return (
        "You are a feed schedule optimization assistant. "
        "Your task is to analyze the projected feed balance for a batch "
        "and suggest date moves for scheduled deliveries so that the "
        "projected balance stays within the minimum and maximum thresholds. "
        "Respect all grouping, ordering, and production weekday constraints.\n\n"
        f"Today's date is {today}."
    )


def _build_balances_section(context: SuggestionContext) -> str:
    lines = ["## Daily Projected Balances", ""]
    lines.append("| Date | Projected Balance (Kg) | Consumption (Kg) " "| Scheduled Delivery (Kg) |")
    lines.append("| --- | --- | --- | --- |")
    for db in context.daily_balances:
        lines.append(
            f"| {db.date} | {db.projected_balance_kg} | {db.consumption_kg} " f"| {db.scheduled_delivery_kg} |"
        )
    return "\n".join(lines)


def _build_deliveries_section(context: SuggestionContext) -> str:
    lines = ["## Scheduled Deliveries", ""]
    lines.append("| Date | Feed Type | Quantity (Kg) |")
    lines.append("| --- | --- | --- |")
    for entry in context.scheduled_entries:
        desc = entry.feed_description or entry.feed_type
        lines.append(f"| {entry.planned_date} | {desc} " f"| {entry.expected_amount_kg} |")
    return "\n".join(lines)


def _build_rules_section(context: SuggestionContext) -> str:
    lines = ["## Business Rules", ""]

    # Threshold rules
    lines.append("### Thresholds")
    lines.append(
        f"- Minimum feed balance threshold: {context.min_threshold} Kg. "
        "The projected balance must not fall below this value."
    )
    lines.append(
        f"- Maximum feed balance threshold: {context.max_threshold} Kg. "
        "The projected balance must not exceed this value."
    )

    lines.append("")

    # Balance calculation rule
    lines.append("### Projected Balance Calculation")
    lines.append(
        "- The projected balance for a day equals the previous day's projected balance "
        "plus the current day's scheduled delivery minus the current day's consumption."
    )
    lines.append(
        "- When you suggest moving a schedule from one date to another, the scheduled delivery "
        "is removed from the original date and added to the new date. You must recalculate "
        "the projected balance for all affected days to ensure thresholds are respected."
    )

    lines.append("")

    # Grouping and ordering rules
    lines.append("### Feed Type Grouping and Ordering Constraints")
    lines.append("- Entries of the same feed type form a group. " "The relative order of groups cannot change.")
    lines.append(
        "- An entry can be moved up to the first delivery date of the next " "feed type group, but not beyond it."
    )
    lines.append(
        "- More than one move is allowed to keep the balance within "
        "thresholds, as long as ordering constraints are respected."
    )

    lines.append("")

    # Production weekday rules
    lines.append("### Production Weekday Constraints")
    lines.append(
        "- A delivery can only be moved to a date whose weekday matches " "one of the feed type's production weekdays."
    )
    lines.append(
        "- If a proposed new date falls on a weekday when the feed type "
        "is not produced, select an alternative date that satisfies the "
        "production weekday constraint."
    )

    lines.append("")
    lines.append("Production weekdays per feed type:")
    for group in context.feed_type_groups:
        weekday_names = [_WEEKDAY_NAMES[w] for w in group.production_weekdays]
        lines.append(f"- {group.feed_type}: {', '.join(weekday_names) if weekday_names else 'none'}")

    lines.append("")

    # Minimum lead time rule
    lines.append("### Minimum Lead Time")
    lines.append(
        "- Only schedules with a planned_date at least 2 days after the current date "
        "can be moved. Schedules for today or tomorrow must remain unchanged."
    )

    lines.append("")

    # Feed type group details
    lines.append("### Feed Type Groups (in order)")
    for i, group in enumerate(context.feed_type_groups):
        next_group_first_date = (
            context.feed_type_groups[i + 1].first_date if i + 1 < len(context.feed_type_groups) else "N/A"
        )
        lines.append(
            f"- Group {i + 1}: {group.feed_type} "
            f"(from {group.first_date} to {group.last_date}, "
            f"next group starts: {next_group_first_date})"
        )

    return "\n".join(lines)


def _build_strategy_section() -> str:
    lines = ["## Strategy", ""]
    lines.append("Follow this approach to resolve threshold violations:")
    lines.append("")
    lines.append("### Over Maximum Threshold (balance too high)")
    lines.append("1. Identify the date where the projected balance exceeds the maximum threshold.")
    lines.append(
        "2. Move the scheduled delivery on that date to a later date until the "
        "new projected balance on the original date falls below the maximum threshold."
    )
    lines.append(
        "3. If the new date for this delivery falls after the start of the next "
        "feed type group, push the schedules of that next feed type group forward "
        "as needed and recalculate the projected balance."
    )
    lines.append("")
    lines.append("### Under Minimum Threshold (balance too low)")
    lines.append("1. Identify the date where the projected balance falls below the minimum threshold.")
    lines.append("2. Find the last scheduled delivery of the same feed type that occurs " "before the offending date.")
    lines.append(
        "3. Move that delivery earlier to the offending date (or the nearest valid "
        "production weekday) and recalculate the projected balance."
    )
    lines.append("")
    lines.append(
        "After each move, recalculate the full projected balance table to check "
        "for new violations. Repeat until all dates are within thresholds or no "
        "further valid moves are possible."
    )
    return "\n".join(lines)


def _build_output_section() -> str:
    lines = ["## Output Format", ""]
    lines.append("Your response must have two sections:")
    lines.append("")
    lines.append("### Section 1: Moves")
    lines.append("Output move lines in the following format, one per line:")
    lines.append("Move schedule from <planned_date> with <feed_description> to <new_planned_date>")
    lines.append("")
    lines.append("Suggest multiple moves when needed to keep the balance within " "the minimum and maximum thresholds.")
    lines.append(
        "Minimize the number of moves — only suggest a move when it is strictly necessary "
        "to keep the projected balance within thresholds."
    )
    lines.append("")
    lines.append('If no changes are needed, output exactly: "No changes needed" and skip Section 2.')
    lines.append("")
    lines.append("### Section 2: New Projected Balance Table")
    lines.append(
        "After the moves, output the updated projected balance table reflecting "
        "all suggested moves. Use the same format as the Daily Projected Balances table above:"
    )
    lines.append("")
    lines.append("| Date | Projected Balance (Kg) | Consumption (Kg) | Scheduled Delivery (Kg) |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("")
    lines.append("Only include dates where the projected balance changed compared to the original table.")
    lines.append("")
    lines.append("Do not include any other text, explanations, or commentary.")
    return "\n".join(lines)
