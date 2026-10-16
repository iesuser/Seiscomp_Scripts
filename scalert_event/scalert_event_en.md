# scalert_event — automatic notification for SeisComP earthquakes

[ქართული ვერსია](scalert_event_ka.md)

This document describes the architecture: `scalert` calls our script and passes it the
`event_id`; the script reads the earthquake parameters from the SeisComP database, decides
by rules whether a notification should be sent, to whom and with what text — and sends it.

Example texts that the system itself produces (location, decision reason, message body)
are kept in Georgian, exactly as they appear in emails, SMS and logs.

## 1. Overview

```
SeisComP (scautoloc / scevent / scmag ...)
        │  new or updated event
        ▼
scalert ──► scalert_event.py "<message>" <flag> <event_id> <arrivals> <magnitude>
                 │
                 ▼
          [1] read arguments, log RECEIVED
                 │
                 ▼
          [2] seiscomp_db.load_event(event_id)       SeisComP MySQL database
                 │   EventData (time, lat, lon, depth, mode, magnitudes)
                 ▼
          [3] automate_events.process_event(...)     decision
                 │      ├── rules.decide             who receives it and why
                 │      ├── location.py              Georgian location text
                 │      ├── acceleration.py          how strongly it is felt
                 │      └── borders_db.py + geo.py   ies_borders database, geometry
                 │   EventAssessment (audience, reason, location_ge, ...)
                 ▼  only if audience is all or staff
          [4] send_notification                      text + recipients + sending
                 ├── ies_mail_sender                 email (email_recipients.json)
                 └── ies_sms_sender                  SMS   (sms_recipients.json)
```

Email and SMS go to the same group (`staff` or `all`), chosen by the rules. The channels
are independent: if one fails, the other is still sent.

Every step is written to `logs/event_scalert.log`, one line per step with a keyword
(see section 8).

Each call is processed independently: every recalculation of an event that meets the
criteria is sent (see section 6).

Principle: **deciding and sending are separate.** `automate_events` only decides and
sends nothing; `send_notification` only sends and decides nothing. A new rule is added in
`rules.py`, a new channel (e.g. Telegram) in `send_notification`, without affecting each other.

## 2. How scalert calls the script

On event creation and on every update, `scalert` runs the script configured in
`scripts.event` with the following arguments:

| Argument | Meaning |
|----------|---------|
| `$1` | text message (in scalert's format) |
| `$2` | `1` — new event, `0` — update |
| `$3` | event publicID, e.g. `ies2026rudf` — **this is our `event_id`** |
| `$4` | number of arrivals (phases) |
| `$5` | magnitude (may be missing) |

Configuration (`~/seiscomp/etc/scalert.cfg` or via `scconfig`):

```
scripts.event = /home/sysop/Clone/Seiscomp_Scripts/scalert_event/scalert_event.py
```

Requirements for the script:

- the file is executable (`chmod +x`) and its first line is a shebang pointing to the
  correct Python (the venv's python if needed);
- the script relies only on `$3` (event_id). It logs `$5` and `$4`, but takes all
  parameters for the decision from the database, so there is a single source of truth;
- the script never fails silently: any error is logged as `FAILED` (with traceback) and
  the script exits with a non-zero code.

## 3. Step 1 — entry point: `scalert_event.py`

It only orchestrates; there is no business logic here:

1. reads the arguments; if `event_id` is empty → `FAILED`, exit code `2`;
2. writes `RECEIVED event_id=... flag=new|update arrivals=... magnitude=...`;
3. calls steps 2–4 in order.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | processed (sent, or decided not to send) |
| `1` | error during processing (database, mail, ...) |
| `2` | invalid arguments |

## 4. Step 2 — data from the SeisComP database: `seiscomp_db.py`

`load_event(event_id) -> EventData`

```
Event (publicID = event_id)
  ├── preferredOriginID     ──► Origin: time, latitude, longitude, depth, evaluationMode
  └── preferredMagnitudeID  ──► Magnitude (preferred)
Origin._oid ──► Magnitude._parent_oid: all magnitudes of this origin (ML, M, Mw, ...)
```

- we use `Event.preferredOriginID`, not the "newest" origin — the preferred origin is
  the one SeisComP itself considers best;
- SQL queries are parameterized (`cursor.execute(sql, (event_id,))`), not built with `%`
  formatting;
- **race condition:** scalert receives the event via messaging, while `scdb` writes to the
  database asynchronously. So the event or its preferred origin may not be in the database
  yet. `load_event` retries several times with a short pause (e.g. 5 attempts × 3 seconds);
  if it still cannot find it → `LookupError`, `FAILED` in the log.

`EventData` (dataclass):

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | str | publicID |
| `origin_time` | datetime | UTC |
| `latitude`, `longitude` | float | degrees |
| `depth` | float | km |
| `evaluation_mode` | str | `automatic` / `manual` |
| `event_type` | str \| None | `Event.type`; `not existing`, `not locatable`, `outside of network interest` → `SKIPPED` |
| `magnitudes` | dict[str, float] | e.g. `{"ML": 3.4, "M": 3.4}` |
| `preferred_magnitude_type` | str \| None | type of the preferred magnitude |

Log: `INPUT event_id=... origin_time=... lat=... lon=... depth=... mode=... magnitudes=...`

## 5. Step 3 — decision: `automate_events/`

`process_event(origin_time, lat, lon, depth, evaluation_mode, magnitudes) -> EventAssessment`

- checks that latitude, longitude and depth are numbers;
- time is in UTC; +4 hours (Georgian time) is added for the message;
- the mode is converted to the text `Automatic` / `Manual`;
- magnitude selection: `ML` first, otherwise `M`, otherwise the first available one;
  rounded to two decimals;
- a connection to the `ies_borders` database is opened, `rules.decide` is called, and the
  connection is closed.

`EventAssessment`:

| Field | Description |
|-------|-------------|
| `audience` | `all`, `staff` or `None` (nobody) |
| `send` | `audience is not None` |
| `publish` | whether it is published on the website (only for `all`) |
| `location_ge` | Georgian location text (only when something is sent) |
| `ev_mode`, `magnitude_type`, `magnitude`, `local_time` | for the text |
| `reason` | Georgian reason with numbers — why this decision was made |

### 5.1 Rules — `rules.py`

Two recipient groups:

- **everyone (`all`)** — staff and external recipients; the earthquake is published on the website;
- **staff only (`staff`)** — the text starts with `STAFF ONLY.`; not published on the website.

Epicenter inside Georgia:

| Condition | Sent to |
|-----------|---------|
| magnitude ≥ 3.0 | everyone |
| inside Tbilisi and 2.8 ≤ magnitude < 3.0 | everyone |
| inside Tbilisi and magnitude < 2.8 | nobody |
| outside Tbilisi and 2.8 ≤ magnitude < 3.0 | staff only |
| outside Tbilisi, magnitude < 2.8, felt in Tbilisi like M2.8 or more | everyone |
| outside Tbilisi, magnitude < 2.8, felt only weakly in Tbilisi | nobody |

Epicenter abroad:

| Condition | Sent to |
|-----------|---------|
| felt at the border like an M3.0 or larger earthquake inside Georgia | everyone |
| not the case, but ≤ 100 km from the border and magnitude ≥ 3.0 | staff only |
| otherwise | nobody |

The thresholds (2.8, 3.0, 100 km) are constants at the top of `rules.py`.

### 5.2 What "felt like M2.8 / M3.0" means — `acceleration.py`

We compute the acceleration the earthquake produces at a specific place (the Tbilisi
boundary, or the nearest point of the Georgian border), taking distance and depth into
account, and compare it with a "reference" — an earthquake of the threshold magnitude that
happened exactly at that place. If the real earthquake shakes that place no less than the
reference, the threshold is reached.

```
log10(a) = -4.4983 + 1.3209·M − 0.0656·M² − 0.0041·R − 0.5229·log10(R²)
```

`R` — hypocentral distance in km (epicentral distance, depth and a 3 km pseudo-depth).

### 5.3 Location text — `location.py`

Built only when something is sent (to avoid unnecessary database queries).

| Case | Format |
|------|--------|
| in Georgia, ≥ 3.0 | `საქართველო. ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ.` |
| in Tbilisi | `საქართველო.თბილისი, ვაკე-საბურთალოს რაიონი.` |
| outside Tbilisi, < 3.0 | `საქართველო. თბილისიდან Xკმ.` (or `თბილისის საზღვარი.` if < 3 km) + city and settlement |
| abroad | `ტაო-კლარჯეთი, საქართველოს საზღვრიდან 85კმ. დაბა შუახევი, სამხრეთით:104კმ. სოფელი წელათი:90კმ.` |

- distance to a city = distance to its center − city radius − 1 km; if the epicenter is
  inside the city, only the city is written;
- 1 km is subtracted from the distance to a settlement (legacy format), so `0კმ` or `-1კმ`
  can appear;
- the direction is given from the city towards the epicenter;
- borders, cities and settlements are read from the `ies_borders` database (`borders_db.py`),
  calculations are in `geo.py`.

Log:

```
DECISION event_id=... SEND to=all|staff publish=... magnitude=... location=... reason: ...
DECISION event_id=... NOT SENT magnitude=... reason: ...
```

## 6. Repeated recalculations of one event

scalert calls the script on **every** update (new origin, new magnitude, manual review).
Each call independently goes through steps 2–4: fresh data is read from the database, the
rules are evaluated again, and if the result meets the criteria the notification is sent —
regardless of whether the previous recalculation was sent.

So one earthquake may produce several emails and SMS, each with the data of that moment
(magnitude, location, recipient group). This is intentional: each recalculation is a
separate notification. If a recalculation no longer meets the criteria, it is not sent, but
the previous email is not "cancelled".

If two calls arrive at the same time, both are processed separately.

## 7. Step 4 — sending the notification: `send_notification/`

| File | What it does |
|------|--------------|
| `message.py` | `build_subject`, `build_body(assessment, lat, lon)`, `build_sms_text` — text only |
| `recipients.py` | `recipient_emails(audience)`, `recipient_numbers(audience)` — recipients (see section 10) |
| `mailer.py` | SMTP sending with the `MAIL_*` parameters from `.env` |
| `ies_mail_sender.py` | `send_event_mail(...)` — email: text + recipients + SMTP, with logging |
| `ies_sms_sender.py` | `send_event_sms(...)` and `SmsSender` — SMS sending, with logging |

### Email

- one message is sent to everyone, but recipients cannot see each other's addresses;
- `staff` — staff only; `all` — all active recipients.

Subject:

```
Earthquake - Automatic: 2026-10-07 05:15:03. mag=3.0M
```

Body (`STAFF ONLY.` only in the staff case):

```
STAFF ONLY.
Automatic: 2026-10-07 05:15:03. mag=3.0M. ტაო-კლარჯეთი, საქართველოს საზღვრიდან 85კმ. დაბა შუახევი, სამხრეთით:104კმ. სოფელი წელათი:90კმ.
https://www.google.com/maps/place/40.68,42.27
Shakemap: https://shorturl.at/ibvtX

https://ies.iliauni.edu.ge/?page_id=121


ილიას სახელმწიფო უნივერსიტეტი
დედამიწის შემსწავლელ მეცნიერებათა ინსტიტუტი და სეისმური მონიტორინგის ეროვნული ცენტრი
```

Log:

| Entry | Meaning |
|-------|---------|
| `MAIL SENDING` | who it is sent to: count, addresses, subject |
| `MAIL SENT` | successfully handed over to SMTP |
| `MAIL NOT SENT` | there is no active address in the group |
| `MAIL FAILED` | SMTP error (traceback in the same log) |

If sending fails (`MAIL FAILED`), the same notification is not retried; the next
recalculation is processed as usual.

### SMS

The text is the first lines of the email, as in the old system (`STAFF ONLY.` only for staff):

```
STAFF ONLY.
Automatic: 2026-09-08 08:52:15. mag=4.23ML. საქართველო. ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ.
```

Numbers are read from `sms_recipients.json` and converted to the format `995XXXXXXXXX`
(both `+995 555 12-34-56` and `555123456` are accepted; an invalid number is shown in the
log and skipped).

Sending goes through a chain of providers (`SMS_PROVIDERS`, default `magti,smsoffice,gsm`);
each next provider receives **only the numbers the previous one failed to send to**:

| Provider | How | Success |
|----------|-----|---------|
| `magti` | Magti one-way gateway, one number at a time | response `0000-<id>` and, after 5 seconds, tracking status `1`, `4` or `8` |
| `smsoffice` | smsoffice.ge API, one number at a time, up to 3 attempts | `{"Success": true}` |
| `gsm` | GSM modem (iesresource), one request for all remaining numbers | HTTP 200 |

- a provider whose password/key in `.env` is empty is skipped;
- an unconfirmed Magti SMS is passed on to the next provider, so occasionally one SMS may
  arrive twice — for an alert this is better than missing it;
- smsoffice limits the text to 160 characters (error 40); a long Georgian location text may
  come close to this — the length is shown in the log as `length=`;
- after sending, the smsoffice balance is checked; if it is below `SMSOFFICE_BALANCE_WARNING`,
  `SMS BALANCE LOW` is written to the log.

Log:

| Entry | Meaning |
|-------|---------|
| `SMS SENDING` | numbers, text and its length |
| `SMS magti/smsoffice/gsm ...` | result per number per provider |
| `SMS via <provider>: sent=N failed=M` | provider totals |
| `SMS SENT` | sent to all numbers |
| `SMS NOT SENT` | there is no active number in the group |
| `SMS FAILED` | no provider could send to some numbers (the numbers are listed) |
| `SMS BALANCE LOW` | few SMS left on smsoffice |

### Adding to the site: `send_eq2api/`

Only publishable events (the notification goes to everyone) are added to the
iesdata site; if the site already has the same `seiscomp_oid`, it is updated.

| File | What it does |
|------|--------------|
| `event_sender.py` | `send_event_api(...)` — SeisComP event in the site's format (magnitude codes, rounding), with logging |
| `send_eq2api.py` | `EventApiClient` — validation, create / update, deleting a half-created event |

- magnitude types match the site codes case-insensitively (`MLv` → `MLV`); `Ms_20` → `MS`;
  `mB` and types the site does not know (e.g. `Mwp`) are not sent;
- rounding: magnitude 3 decimals, coordinates 5, depth 3;
- if a magnitude of a new event fails, the event is deleted again (all or nothing);
- manual check (read-only): `./send_eq2api/send_eq2api.py ies2026ufhk`.

| Entry | Meaning |
|-------|---------|
| `API SENDING` | the data being sent |
| `API CREATED` / `API UPDATED` | added to / updated on the site, with `site_id` |
| `API ... not sent: ...` | magnitude types unknown to the site, skipped |
| `API NOT SENT` | no magnitude the site knows |
| `API FAILED` | API error, with traceback |

## 8. Reading the log

File: `logs/event_scalert.log`. Line format: `time LEVEL KEYWORD event_id=... ...`

| Keyword | Meaning |
|---------|---------|
| `RECEIVED` | scalert called the script, with its arguments |
| `INPUT` | data read from the database |
| `DECISION` | `SEND` or `NOT SENT`, with a Georgian reason |
| `WAITING` | the event is not yet fully written to the database, retrying |
| `SKIPPED` | not processed (fake event, or no magnitude yet) |
| `MAIL ...` | email recipients and sending result |
| `SMS ...` | SMS numbers, providers and sending result |
| `API ...` | result of adding the event to the site |
| `FAILED` | error, with traceback |

Example:

```
RECEIVED event_id=ies2026rudf flag=new arrivals=12 magnitude=4.2
INPUT event_id=ies2026rudf origin_time=2026-09-08 04:52:15 lat=41.607 lon=43.5676 depth=15.3 mode=automatic magnitudes={'ML': 4.23}
DECISION event_id=ies2026rudf SEND to=all publish=True magnitude=4.23ML local_time=2026-09-08 08:52:15 location=საქართველო. ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ. reason: ეპიცენტრი საქართველოშია და მაგნიტუდა 4.23 ≥ 3.0
MAIL SENDING event_id=ies2026rudf audience=all count=2 recipients=... subject='Earthquake - Automatic: 2026-09-08 08:52:15. mag=4.23ML'
MAIL SENT event_id=ies2026rudf audience=all count=2
SMS SENDING event_id=ies2026rudf audience=all count=3 numbers=... length=119 text='Automatic: ...'
SMS via magti: sent=3 failed=0
SMS SENT event_id=ies2026rudf audience=all count=3
RECEIVED event_id=ies2026rudf flag=update arrivals=15 magnitude=4.3
INPUT event_id=ies2026rudf ... magnitudes={'ML': 4.31}
DECISION event_id=ies2026rudf SEND to=all ... magnitude=4.31ML ...
MAIL SENDING event_id=ies2026rudf audience=all count=2 ...
MAIL SENT event_id=ies2026rudf audience=all count=2
```

To find a specific earthquake: `grep ies2026rudf logs/event_scalert.log`.

Manual run for testing (without scalert):

```
./scalert_event.py "manual test" 1 ies2026rudf 0
./scalert_event.py --dry-run ies2026rudf     # decides and logs, but sends nothing
```

## 9. Configuration — `.env`

All passwords and addresses live only in `.env` (not added to git); nothing is hardcoded.
`config.py` reads `.env` and provides it to the other modules.

| Variable | Purpose |
|----------|---------|
| `SC_DB_HOST`, `SC_DB_USER`, `SC_DB_PASSWORD`, `SC_DB_NAME` | SeisComP database |
| `BORDERS_DB_HOST`, `BORDERS_DB_USER`, `BORDERS_DB_PASSWORD`, `BORDERS_DB_NAME` | borders database |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP |
| `RECIPIENTS_FILE` | email recipients, default `recipients/email_recipients.json` (see section 10) |
| `SMS_RECIPIENTS_FILE` | SMS recipients, default `recipients/sms_recipients.json` |
| `Recp_Exporter_API_URL`, `Recp_Exporter_API_KEY` | iesdata API from which recipients are updated |
| `Recp_Exporter_API_CA` | only for a self-signed server certificate; system CAs by default |
| `Send_eq2api_API_URL`, `Send_eq2api_API_KEY` | iesdata API where publishable events are added |
| `SEND_EQ2API` | `0` — events are not added to the site |
| `LOG_LEVEL` | with `DEBUG`, the inputs to the rules are also logged |
| `SEND_EMAIL`, `SEND_SMS` | `0` — the channel is disabled (both enabled by default) |
| `SMS_PROVIDERS` | order of SMS providers, `magti,smsoffice,gsm` |
| `MAGTI_USERNAME`, `MAGTI_PASSWORD`, `MAGTI_CLIENT_ID`, `MAGTI_SERVICE_ID` | Magti gateway |
| `SMSOFFICE_KEY`, `SMSOFFICE_SENDER`, `SMSOFFICE_BALANCE_WARNING` | smsoffice.ge |
| `GSM_SMS_URL`, `GSM_SMS_CODE` | GSM modem service |
| `DRY_RUN` | `1` — nothing is sent, log only |

## 10. Recipients

Recipients are managed from the Notify page (iesdata). `recipients/update_recipients.py`
creates two local files from the API (neither is added to git):

```
iesdata API  GET /api/recips/  (X-API-Key)
     │   {"items": [{username, is_staff, is_active,
     │               emails:  [{email, is_active}],
     │               numbers: [{phone_number, is_active}]}], "total": N}
     ▼
recipients/update_recipients.py      (periodically, via cron)
     │                      │
     ▼                      ▼
email_recipients.json    sms_recipients.json
(one entry per address)  (one entry per number)
     │
     ▼
send_notification/recipients.py      (on every email and SMS send)
```

| File | `.env` | Example |
|------|--------|---------|
| `recipients/email_recipients.json` | `RECIPIENTS_FILE` | `recipients/email_recipients.example.json` |
| `recipients/sms_recipients.json` | `SMS_RECIPIENTS_FILE` | `recipients/sms_recipients.example.json` |

Format:

```json
[
  {"username": "...", "email": "a@iliauni.edu.ge", "is_staff": true,  "is_active": true},
  {"username": "...", "email": "b@example.com",    "is_staff": false, "is_active": true}
]
```

```json
[
  {"username": "...", "phone_number": "+995555000001", "is_staff": true, "is_active": true}
]
```

- an entry is active only if **both the recipient and the address/number** are active;
- the `staff` group gets only `is_staff: true`; `all` gets every active entry;
- the file is read on every send, so an update takes effect immediately.

`update_recipients.py`:

```
./recipients/update_recipients.py            # read from the API and update both files
./recipients/update_recipients.py --dry-run  # preview only, files are not changed
```

- a file is replaced only after a successful response, and atomically (first `.tmp`, then rename);
- if the API is unreachable, **both old files are kept**; if one of the lists has no active
  entries, **only that file is kept as is**, the other is updated normally (exit code `1`
  in both cases); to write an empty list use `--allow-empty`;
- the API server has a Let's Encrypt certificate (since 2026-10-15), verified with the
  system CAs; `Recp_Exporter_API_CA` is only needed for a self-signed certificate;
- log: `logs/update_recipients.log` — `UPDATED`, `UNCHANGED`, `FAILED`.

cron example (every 10 minutes), `crontab -e`:

```
*/10 * * * * /home/sysop/Clone/Seiscomp_Scripts/scalert_event/recipients/update_recipients.py >/dev/null 2>&1
```

## 11. File structure

```
scalert_event/
├── scalert_event.py          entry point (called by scalert)
├── config.py                 reads .env
├── seiscomp_db.py            load_event(event_id) -> EventData
├── .env                      passwords (not in git); template — .env.example
├── requirements.txt          pymysql, pytest
├── recipients/
│   ├── update_recipients.py  updates both files from the API
│   ├── email_recipients.json email recipients (not in git); template — email_recipients.example.json
│   └── sms_recipients.json   SMS recipients (not in git); template — sms_recipients.example.json
├── venv/                     Python environment (not in git)
├── automate_events/
│   ├── __init__.py
│   ├── automate_event.py     process_event, EventAssessment
│   ├── rules.py              who receives it and why
│   ├── location.py           Georgian location text
│   ├── acceleration.py       acceleration formula
│   ├── borders_db.py         ies_borders database
│   └── geo.py                distance, direction, polygon
├── send_notification/
│   ├── message.py            subject, email and SMS text
│   ├── recipients.py         recipients (emails and numbers)
│   ├── mailer.py             SMTP
│   ├── ies_mail_sender.py    send_event_mail
│   └── ies_sms_sender.py     send_event_sms, SmsSender (magti → smsoffice → gsm)
├── send_eq2api/
│   ├── event_sender.py       send_event_api (SeisComP → site format)
│   └── send_eq2api.py        EventApiClient (iesdata API)
├── logs/                     event_scalert.log, update_recipients.log
└── tests/
```

## 12. Installation and running

```
cd /home/sysop/Clone/Seiscomp_Scripts/scalert_event
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env                       # fill in passwords and API keys
chmod +x scalert_event.py recipients/update_recipients.py
./recipients/update_recipients.py          # first download of recipients
./venv/bin/python -m pytest -q             # tests (no database or SMTP needed)
./scalert_event.py --dry-run <event_id>    # with the real database, without sending
```

The shebang of `scalert_event.py` points to `venv/bin/python` (absolute path), so scalert
needs no extra parameters. If the folder is moved, the shebang must be updated.

Finally, the script is set in the scalert configuration (`scripts.event`, section 2) and
scalert is restarted: `seiscomp restart scalert`. For the recipients update cron entry,
see section 10.
