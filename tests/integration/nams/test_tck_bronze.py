"""TCK Bronze-tier conformance — short-term memory core.

Placeholder pending publication of the TCK reference Docker image.
Replace the skip with concrete assertions against SPEC method behaviour
once the image is available. See tests/integration/nams/README.md.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_bronze_tier_placeholder(nams_credentials) -> None:
    pytest.skip(
        "TCK Bronze tier suite not implemented yet — pending TCK reference "
        "Docker image publication."
    )
