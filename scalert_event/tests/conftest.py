import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automate_events import Audience, EventAssessment  # noqa: E402


@pytest.fixture
def make_assessment():
    def make(audience=Audience.ALL, magnitude=3.2, location="საქართველო. ქალაქი გორი:5კმ."):
        return EventAssessment(
            audience=audience,
            publish_iliauni=audience is Audience.ALL,
            send_api=audience is not None,
            location_ge=location if audience else None,
            ev_mode="Automatic",
            magnitude_type="ML",
            magnitude=magnitude,
            local_time=datetime(2026, 10, 7, 9, 15, 3),
            reason="test",
            location_en="Georgia. Gori (city)." if audience else None,
        )

    return make
