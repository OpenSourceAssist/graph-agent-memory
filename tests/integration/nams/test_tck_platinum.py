"""TCK Platinum-tier conformance — hosted-only operations.

Placeholder pending publication of the TCK reference Docker image.
Platinum surface includes ``set_entity_feedback``, ``get_entity_history``,
``get_entity_provenance``, ``bulk_add_messages``, ``get_observations``,
``get_reflections``, ``create_conversation``, ``list_conversations``, and
``cypher_query``.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_platinum_tier_placeholder(nams_credentials) -> None:
    pytest.skip(
        "TCK Platinum tier suite not implemented yet — pending TCK reference "
        "Docker image publication."
    )
