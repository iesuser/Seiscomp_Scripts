"""Automatic earthquake processing: who to notify and how to describe the location.

How an automatic event flows through the system:

1. scalert calls `scalert_event.py` with the event's publicID.
2. `scalert_event.py` loads the event from the SeisComP database
   (`seiscomp_db.load_event`) and calls `process_event` from this package.
3. `process_event` (automate_event.py) validates the inputs, picks the preferred
   magnitude and asks `rules.decide` who should be notified.
4. `rules` uses `location.LocationService` to answer spatial questions
   ("is it in Georgia?", "how far is Tbilisi?") and to build the Georgian
   location text. `LocationService` reads polygons, cities and settlements
   through `borders_db.BordersRepository` and does the maths in `geo`.
   Ground-motion comparisons come from `acceleration`.
5. If the event must be sent, `send_notification.ies_mail_sender` emails it.

Every step logs to `logs/event_scalert.log`.
"""

from .automate_event import EventAssessment, process_event
from .rules import Audience

__all__ = ["Audience", "EventAssessment", "process_event"]
