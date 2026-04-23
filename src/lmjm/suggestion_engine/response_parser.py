import re

from lmjm.model.feed_schedule_suggestion import Suggestion

_MOVE_PATTERN = re.compile(r"Move schedule from (\S+) with (.+) to (\S+)")


def parse_suggestions(response_text: str) -> list[Suggestion]:
    """Parse Bedrock response text into a list of Suggestion objects.

    Extracts lines matching the pattern:
        "Move schedule from <planned_date> with <feed_type> to <new_planned_date>"

    Returns an empty list if no matching lines are found.
    """
    suggestions: list[Suggestion] = []
    for line in response_text.splitlines():
        match = _MOVE_PATTERN.search(line)
        if match:
            suggestions.append(
                Suggestion(
                    planned_date=match.group(1),
                    feed_type=match.group(2),
                    new_planned_date=match.group(3),
                    description=line.strip(),
                )
            )
    return suggestions
