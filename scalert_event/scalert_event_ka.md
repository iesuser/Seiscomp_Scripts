# scalert_event — ავტომატური შეტყობინება SeisComP-ის მიწისძვრაზე

[English version](scalert_event_en.md)

ეს დოკუმენტი აღწერს არქიტექტურას: `scalert` იძახებს ჩვენს სკრიპტს და გადასცემს
`event_id`-ს; სკრიპტი SeisComP-ის ბაზიდან იღებს მიწისძვრის პარამეტრებს, წესების
მიხედვით წყვეტს — უნდა გაიგზავნოს თუ არა შეტყობინება, ვის და რა ტექსტით — და აგზავნის.

## 1. მოკლედ

```
SeisComP (scautoloc / scevent / scmag ...)
        │  ახალი ან განახლებული event
        ▼
scalert ──► scalert_event.py "<message>" <flag> <event_id> <arrivals> <magnitude>
                 │
                 ▼
          [1] არგუმენტების წაკითხვა, ლოგი RECEIVED
                 │
                 ▼
          [2] seiscomp_db.load_event(event_id)       SeisComP-ის MySQL ბაზა
                 │   EventData (დრო, lat, lon, სიღრმე, რეჟიმი, მაგნიტუდები)
                 ▼
          [3] automate_events.process_event(...)     გადაწყვეტილება
                 │      ├── rules.decide             ვის ეგზავნება და რატომ
                 │      ├── location.py              ქართული ლოკაციის ტექსტი
                 │      ├── acceleration.py          რამდენად იგრძნობა
                 │      └── borders_db.py + geo.py   ies_borders ბაზა, გეომეტრია
                 │   EventAssessment (audience, reason, location_ge, ...)
                 ▼  მხოლოდ თუ audience არის all ან staff
          [4] send_notification                      ტექსტი + მიმღებები + გაგზავნა
                 ├── ies_mail_sender                 მეილი  (email_recipients.json)
                 └── ies_sms_sender                  SMS    (sms_recipients.json)
```

მეილიც და SMS-იც ერთსა და იმავე ჯგუფს ეგზავნება (`staff` ან `all`), რომელსაც წესები
ადგენს. არხები ერთმანეთისგან დამოუკიდებელია: თუ ერთი ვერ გაიგზავნა, მეორე მაინც იგზავნება.

ყველა ნაბიჯი იწერება `logs/event_scalert.log`-ში, თითო ხაზი ერთი საკვანძო სიტყვით
(იხ. ნაწილი 8).

ყოველი გამოძახება დამოუკიდებლად მუშავდება: event-ის ყოველი გადათვლა, რომელიც
კრიტერიუმებს აკმაყოფილებს, იგზავნება (იხ. ნაწილი 6).

პრინციპი: **გადაწყვეტილება და გაგზავნა ცალ-ცალკეა.** `automate_events` მხოლოდ წყვეტს
და არაფერს აგზავნის; `send_notification` მხოლოდ აგზავნის და არაფერს წყვეტს. ახალი
წესი ემატება `rules.py`-ში, ახალი არხი (მაგ. Telegram) — `send_notification`-ში,
ერთმანეთზე გავლენის გარეშე.

## 2. როგორ იძახებს scalert სკრიპტს

`scalert` event-ის შექმნისას და ყოველი განახლებისას უშვებს `scripts.event`-ში
მითითებულ სკრიპტს შემდეგი არგუმენტებით:

| არგუმენტი | მნიშვნელობა |
|-----------|-------------|
| `$1` | ტექსტური შეტყობინება (scalert-ის ფორმატით) |
| `$2` | `1` — ახალი event, `0` — განახლება |
| `$3` | event-ის publicID, მაგ. `ies2026rudf` — **ეს არის ჩვენი `event_id`** |
| `$4` | arrival-ების (ფაზების) რაოდენობა |
| `$5` | მაგნიტუდა (შეიძლება არ იყოს) |

კონფიგურაცია (`~/seiscomp/etc/scalert.cfg` ან `scconfig`-იდან):

```
scripts.event = /home/sysop/Clone/Seiscomp_Scripts/scalert_event/scalert_event.py
```

მოთხოვნები სკრიპტზე:

- ფაილი გაშვებადია (`chmod +x`) და პირველ ხაზზე აქვს shebang, რომელიც სწორ Python-ს
  მიუთითებს (საჭიროების შემთხვევაში venv-ის python-ს);
- სკრიპტი მხოლოდ `$3`-ს (event_id) ეყრდნობა. `$5`-ს და `$4`-ს წერს ლოგში, მაგრამ
  გადაწყვეტილებისთვის ყველა პარამეტრს ბაზიდან იღებს, რომ ერთ წყაროს ეყრდნობოდეს;
- სკრიპტი არასოდეს "ვარდება" ჩუმად: ნებისმიერი შეცდომა იწერება ლოგში `FAILED`-ით
  (traceback-ით) და სკრიპტი ბრუნდება არანულოვანი კოდით.

## 3. ნაბიჯი 1 — შესვლის წერტილი: `scalert_event.py`

მხოლოდ ორკესტრაციას აკეთებს, ბიზნეს-ლოგიკა აქ არ არის:

1. კითხულობს არგუმენტებს; თუ `event_id` ცარიელია → `FAILED`, გამოსვლის კოდი `2`;
2. წერს `RECEIVED event_id=... flag=new|update arrivals=... magnitude=...`;
3. იძახებს ნაბიჯებს 2–4 თანმიმდევრობით.

გამოსვლის კოდები:

| კოდი | მნიშვნელობა |
|------|-------------|
| `0` | დამუშავდა (გაიგზავნა ან გადაწყდა, რომ არ იგზავნება) |
| `1` | შეცდომა დამუშავებისას (ბაზა, მეილი, ...) |
| `2` | არასწორი არგუმენტები |

## 4. ნაბიჯი 2 — მონაცემები SeisComP-ის ბაზიდან: `seiscomp_db.py`

`load_event(event_id) -> EventData`

```
Event (publicID = event_id)
  ├── preferredOriginID     ──► Origin: time, latitude, longitude, depth, evaluationMode
  └── preferredMagnitudeID  ──► Magnitude (preferred)
Origin._oid ──► Magnitude._parent_oid: ამ origin-ის ყველა მაგნიტუდა (ML, M, Mw, ...)
```

- ვიყენებთ `Event.preferredOriginID`-ს და არა "ყველაზე ახალ" origin-ს — preferred
  origin არის ის, რასაც SeisComP თავად თვლის საუკეთესოდ;
- SQL მოთხოვნები პარამეტრიზებულია (`cursor.execute(sql, (event_id,))`), არა `%`
  ფორმატირებით;
- **რბოლის პირობა:** scalert იღებს event-ს messaging-იდან, ხოლო `scdb` ბაზაში
  ასინქრონულად წერს. ამიტომ event ან მისი preferred origin შეიძლება ბაზაში ჯერ არ
  იყოს. `load_event` ცდილობს რამდენჯერმე მცირე პაუზით (მაგ. 5 ცდა × 3 წამი); თუ
  მაინც ვერ იპოვა → `LookupError`, ლოგში `FAILED`.

`EventData` (dataclass):

| ველი | ტიპი | აღწერა |
|------|------|--------|
| `event_id` | str | publicID |
| `origin_time` | datetime | UTC |
| `latitude`, `longitude` | float | გრადუსი |
| `depth` | float | კმ |
| `evaluation_mode` | str | `automatic` / `manual` |
| `event_type` | str \| None | `Event.type`; `not existing`, `not locatable`, `outside of network interest` → `SKIPPED` |
| `magnitudes` | dict[str, float] | მაგ. `{"ML": 3.4, "M": 3.4}` |
| `preferred_magnitude_type` | str \| None | preferred მაგნიტუდის ტიპი |

ლოგი: `INPUT event_id=... origin_time=... lat=... lon=... depth=... mode=... magnitudes=...`

## 5. ნაბიჯი 3 — გადაწყვეტილება: `automate_events/`

`process_event(origin_time, lat, lon, depth, evaluation_mode, magnitudes) -> EventAssessment`

- ამოწმებს, რომ განედი, გრძედი და სიღრმე რიცხვებია;
- დრო UTC-შია; შეტყობინებისთვის ემატება +4 საათი (საქართველოს დრო);
- რეჟიმი გადაიქცევა `Automatic` / `Manual` ტექსტად;
- მაგნიტუდის არჩევა: ჯერ `ML`, თუ არ არის — `M`, თუ არც ის — პირველი არსებული;
  მრგვალდება ორ ათწილადამდე;
- იხსნება კავშირი `ies_borders` ბაზასთან, გამოიძახება `rules.decide`, კავშირი იხურება.

`EventAssessment`:

| ველი | აღწერა |
|------|--------|
| `audience` | `all`, `staff` ან `None` (არავის) |
| `send` | `audience is not None` |
| `publish` | ქვეყნდება თუ არა საიტზე (მხოლოდ `all`-ისთვის) |
| `location_ge` | ლოკაციის ქართული ტექსტი (მხოლოდ როცა იგზავნება) |
| `ev_mode`, `magnitude_type`, `magnitude`, `local_time` | ტექსტისთვის |
| `reason` | ქართული მიზეზი რიცხვებით — რატომ მიიღო ეს გადაწყვეტილება |

### 5.1 წესები — `rules.py`

მიმღებების ორი ჯგუფი:

- **ყველა (`all`)** — თანამშრომლები და გარე მიმღებები; მიწისძვრა ქვეყნდება საიტზე;
- **მხოლოდ თანამშრომლები (`staff`)** — ტექსტს თავში აწერია `STAFF ONLY.`; საიტზე არ ქვეყნდება.

ეპიცენტრი საქართველოშია:

| პირობა | ვის ეგზავნება |
|--------|---------------|
| მაგნიტუდა ≥ 3.0 | ყველას |
| თბილისშია და 2.8 ≤ მაგნიტუდა < 3.0 | ყველას |
| თბილისშია და მაგნიტუდა < 2.8 | არავის |
| თბილისის გარეთაა და 2.8 ≤ მაგნიტუდა < 3.0 | მხოლოდ თანამშრომლებს |
| თბილისის გარეთაა, მაგნიტუდა < 2.8, თბილისში იგრძნობა როგორც M2.8 ან მეტი | ყველას |
| თბილისის გარეთაა, მაგნიტუდა < 2.8, თბილისში სუსტად იგრძნობა | არავის |

ეპიცენტრი საზღვარგარეთაა:

| პირობა | ვის ეგზავნება |
|--------|---------------|
| საზღვართან იგრძნობა როგორც საქართველოში მომხდარი M3.0 ან მეტი | ყველას |
| ასე არ არის, მაგრამ საზღვრიდან ≤ 100 კმ-ია და მაგნიტუდა ≥ 3.0 | მხოლოდ თანამშრომლებს |
| სხვა შემთხვევაში | არავის |

ზღვრები (2.8, 3.0, 100 კმ) არის კონსტანტები `rules.py`-ის თავში.

### 5.2 რას ნიშნავს „იგრძნობა როგორც M2.8 / M3.0“ — `acceleration.py`

ითვლება, რა აჩქარებას მისცემს მიწისძვრა კონკრეტულ ადგილს (თბილისის საზღვარს ან
საქართველოს საზღვრის უახლოეს წერტილს), მანძილისა და სიღრმის გათვალისწინებით, და
დარდება „ეტალონს“ — ზღვრული მაგნიტუდის მიწისძვრას, რომელიც ზუსტად იმ ადგილას მოხდა.
თუ რეალური მიწისძვრა ამ ადგილს ეტალონზე ნაკლებად არ შეარყევს, ზღვარი მიღწეულია.

```
log10(a) = -4.4983 + 1.3209·M − 0.0656·M² − 0.0041·R − 0.5229·log10(R²)
```

`R` — ჰიპოცენტრული მანძილი კმ-ში (ეპიცენტრული მანძილი, სიღრმე და 3 კმ ფსევდო-სიღრმე).

### 5.3 ლოკაციის ტექსტი — `location.py`

იგება მხოლოდ მაშინ, როცა რამე იგზავნება (ზედმეტი მოთხოვნები ბაზაში რომ არ გაკეთდეს).

| შემთხვევა | ფორმატი |
|-----------|---------|
| საქართველოში, ≥ 3.0 | `საქართველო. ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ.` |
| თბილისში | `საქართველო.თბილისი, ვაკე-საბურთალოს რაიონი.` |
| თბილისის გარეთ, < 3.0 | `საქართველო. თბილისიდან Xკმ.` (ან `თბილისის საზღვარი.`, თუ < 3 კმ) + ქალაქი და დასახლება |
| საზღვარგარეთ | `ტაო-კლარჯეთი, საქართველოს საზღვრიდან 85კმ. დაბა შუახევი, სამხრეთით:104კმ. სოფელი წელათი:90კმ.` |

- ქალაქამდე მანძილი = ცენტრამდე მანძილი − ქალაქის რადიუსი − 1 კმ; თუ ეპიცენტრი ქალაქშია, იწერება მხოლოდ ქალაქი;
- დასახლებამდე მანძილს აკლდება 1 კმ (ძველი ფორმატი), ამიტომ შეიძლება ეწეროს `0კმ` ან `-1კმ`;
- მიმართულება ნაჩვენებია ქალაქიდან ეპიცენტრისკენ;
- საზღვრები, ქალაქები და დასახლებები იკითხება `ies_borders` ბაზიდან (`borders_db.py`),
  გამოთვლები — `geo.py`-ში.

ლოგი:

```
DECISION event_id=... SEND to=all|staff publish=... magnitude=... location=... reason: ...
DECISION event_id=... NOT SENT magnitude=... reason: ...
```

## 6. ერთი event-ის განმეორებითი გადათვლები

scalert სკრიპტს იძახებს **ყოველ** განახლებაზე (ახალი origin, ახალი მაგნიტუდა,
მანუალური გადახედვა). ყოველი გამოძახება დამოუკიდებლად გადის ნაბიჯებს 2–4: ბაზიდან
იკითხება ახალი მონაცემები, წესები თავიდან ითვლება და თუ შედეგი კრიტერიუმებს
აკმაყოფილებს, შეტყობინება იგზავნება — მიუხედავად იმისა, წინა გადათვლაზე გაიგზავნა თუ არა.

ამიტომ ერთ მიწისძვრაზე შეიძლება რამდენიმე მეილი და SMS წავიდეს, თითოეული იმ მომენტის
მონაცემებით (მაგნიტუდა, ლოკაცია, მიმღებების ჯგუფი). ეს განზრახ ასეა: ყოველი გადათვლა
ცალკე შეტყობინებაა. თუ გადათვლა კრიტერიუმებს აღარ აკმაყოფილებს, ის არ იგზავნება,
მაგრამ წინა მეილი არ "უქმდება".

ორი გამოძახება ერთდროულად თუ მოვიდა, ორივე ცალ-ცალკე დამუშავდება.

## 7. ნაბიჯი 4 — შეტყობინების გაგზავნა: `send_notification/`

| ფაილი | რას აკეთებს |
|-------|-------------|
| `message.py` | `build_subject`, `build_body(assessment, lat, lon)`, `build_sms_text` — მხოლოდ ტექსტი |
| `recipients.py` | `recipient_emails(audience)`, `recipient_numbers(audience)` — მიმღებები (იხ. ნაწილი 10) |
| `mailer.py` | SMTP გაგზავნა, `.env`-იდან `MAIL_*` პარამეტრებით |
| `ies_mail_sender.py` | `send_event_mail(...)` — მეილი: ტექსტი + მიმღებები + SMTP, ლოგით |
| `ies_sms_sender.py` | `send_event_sms(...)` და `SmsSender` — SMS-ის გაგზავნა, ლოგით |

### მეილი

- ერთი წერილი იგზავნება ყველასთან, მაგრამ მიმღებები ერთმანეთის მისამართებს ვერ ხედავენ;
- `staff` — მხოლოდ თანამშრომლები; `all` — ყველა აქტიური მიმღები.

თემა:

```
Earthquake - Automatic: 2026-10-07 05:15:03. mag=3.0M
```

ტექსტი (`STAFF ONLY.` მხოლოდ თანამშრომლების შემთხვევაში):

```
STAFF ONLY.
Automatic: 2026-10-07 05:15:03. mag=3.0M. ტაო-კლარჯეთი, საქართველოს საზღვრიდან 85კმ. დაბა შუახევი, სამხრეთით:104კმ. სოფელი წელათი:90კმ.
https://www.google.com/maps/place/40.68,42.27
Shakemap: https://shorturl.at/ibvtX

https://ies.iliauni.edu.ge/?page_id=121


ილიას სახელმწიფო უნივერსიტეტი
დედამიწის შემსწავლელ მეცნიერებათა ინსტიტუტი და სეისმური მონიტორინგის ეროვნული ცენტრი
```

ლოგი:

| ჩანაწერი | მნიშვნელობა |
|----------|-------------|
| `MAIL SENDING` | ვის ეგზავნება: რაოდენობა, მისამართები, თემა |
| `MAIL SENT` | წარმატებით გადაეცა SMTP-ს |
| `MAIL NOT SENT` | ჯგუფში არც ერთი აქტიური მისამართი არ არის |
| `MAIL FAILED` | SMTP-ის შეცდომა (traceback იმავე ლოგში) |

თუ გაგზავნა ვერ მოხერხდა (`MAIL FAILED`), იგივე შეტყობინება ხელახლა არ იცდება;
შემდეგი გადათვლა ჩვეულებრივად დამუშავდება.

### SMS

ტექსტი მეილის პირველი ხაზებია, როგორც ძველ სისტემაში (`STAFF ONLY.` მხოლოდ თანამშრომლებს):

```
STAFF ONLY.
Automatic: 2026-09-08 08:52:15. mag=4.23ML. საქართველო. ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ.
```

ნომრები იკითხება `sms_recipients.json`-იდან და გადაიყვანება ფორმატში `995XXXXXXXXX`
(`+995 555 12-34-56` და `555123456` ორივე მისაღებია; არასწორი ნომერი ლოგში ჩანს და გამოიტოვება).

გაგზავნა ხდება პროვაიდერების ჯაჭვით (`SMS_PROVIDERS`, ნაგულისხმევად `magti,smsoffice,gsm`);
ყოველი შემდეგი პროვაიდერი იღებს **მხოლოდ იმ ნომრებს, რომლებზეც წინამ ვერ გაგზავნა**:

| პროვაიდერი | როგორ | წარმატება |
|------------|-------|-----------|
| `magti` | Magti one-way gateway, თითო ნომერზე | პასუხი `0000-<id>` და 5 წამის შემდეგ tracking სტატუსი `1`, `4` ან `8` |
| `smsoffice` | smsoffice.ge API, თითო ნომერზე, 3 ცდამდე | `{"Success": true}` |
| `gsm` | GSM მოდემი (iesresource), ერთი მოთხოვნით ყველა დარჩენილზე | HTTP 200 |

- პროვაიდერი, რომლის პაროლი/გასაღები `.env`-ში ცარიელია, გამოიტოვება;
- Magti-ს დაუდასტურებელი SMS შემდეგ პროვაიდერზე გადადის, ამიტომ იშვიათად შეიძლება ერთი
  SMS ორჯერ მივიდეს — განგაშისთვის ეს სჯობს გამოტოვებას;
- smsoffice-ს ტექსტი 160 სიმბოლომდე აქვს (შეცდომა 40); ქართული ლოკაციის გრძელი ტექსტი
  შეიძლება ამას მიუახლოვდეს — სიგრძე ლოგში `length=`-ით ჩანს;
- გაგზავნის შემდეგ მოწმდება smsoffice-ის ბალანსი; `SMSOFFICE_BALANCE_WARNING`-ზე ნაკლებისას
  ლოგში იწერება `SMS BALANCE LOW`.

ლოგი:

| ჩანაწერი | მნიშვნელობა |
|----------|-------------|
| `SMS SENDING` | ნომრები, ტექსტი და მისი სიგრძე |
| `SMS magti/smsoffice/gsm ...` | თითო ნომრის შედეგი თითო პროვაიდერზე |
| `SMS via <provider>: sent=N failed=M` | პროვაიდერის ჯამი |
| `SMS SENT` | ყველა ნომერზე გაიგზავნა |
| `SMS NOT SENT` | ჯგუფში არც ერთი აქტიური ნომერი არ არის |
| `SMS FAILED` | ზოგ ნომერზე ვერც ერთმა პროვაიდერმა ვერ გაგზავნა (ნომრები ჩამოთვლილია) |
| `SMS BALANCE LOW` | smsoffice-ზე ცოტა SMS დარჩა |

### საიტზე დამატება: `send_eq2api/`

მხოლოდ გამოსაქვეყნებელი მიწისძვრა (შეტყობინება ყველას ეგზავნება) ემატება iesdata საიტს;
თუ საიტზე იგივე `seiscomp_oid` უკვე არის, განახლდება.

| ფაილი | რას აკეთებს |
|-------|-------------|
| `event_sender.py` | `send_event_api(...)` — SeisComP-ის მიწისძვრა საიტის ფორმატში (მაგნიტუდის კოდები, დამრგვალება), ლოგით |
| `send_eq2api.py` | `EventApiClient` — შემოწმება, შექმნა / განახლება, ჩავარდნისას შექმნილის წაშლა |

- მაგნიტუდის ტიპები საიტის კოდებს ემთხვევა ასოების ზომის მიუხედავად (`MLv` → `MLV`); `Ms_20` → `MS`;
  `mB` და საიტისთვის უცნობი ტიპები (მაგ. `Mwp`) არ იგზავნება;
- დამრგვალება: მაგნიტუდა 3 ათწილადი, კოორდინატები 5, სიღრმე 3;
- ახალ მიწისძვრაზე რომელიმე მაგნიტუდა თუ ჩავარდა, მიწისძვრა იშლება (ყველაფერი ან არაფერი);
- ხელით შემოწმება (მხოლოდ კითხულობს): `./send_eq2api/send_eq2api.py ies2026ufhk`.

| ჩანაწერი | მნიშვნელობა |
|----------|-------------|
| `API SENDING` | გასაგზავნი მონაცემები |
| `API CREATED` / `API UPDATED` | საიტზე დაემატა / განახლდა, `site_id`-ით |
| `API ... not sent: ...` | საიტისთვის უცნობი მაგნიტუდის ტიპები, რომლებიც გამოტოვდა |
| `API NOT SENT` | საიტისთვის ცნობილი არც ერთი მაგნიტუდა არ არის |
| `API FAILED` | API-ის შეცდომა, traceback-ით |

## 8. ლოგის წაკითხვა

ფაილი: `logs/event_scalert.log`. ხაზის ფორმატი: `დრო LEVEL KEYWORD event_id=... ...`

| საკვანძო სიტყვა | ნიშნავს |
|-----------------|---------|
| `RECEIVED` | scalert-მა გამოიძახა სკრიპტი, არგუმენტებით |
| `INPUT` | ბაზიდან წაკითხული მონაცემები |
| `DECISION` | `SEND` ან `NOT SENT`, ქართული მიზეზით |
| `WAITING` | event ბაზაში ჯერ სრულად არ ჩაწერილა, ხელახლა ცდის |
| `SKIPPED` | არ დამუშავდა (არარეალური event ან მაგნიტუდა ჯერ არ აქვს) |
| `MAIL ...` | მეილის მიმღებები და გაგზავნის შედეგი |
| `SMS ...` | SMS-ის ნომრები, პროვაიდერები და გაგზავნის შედეგი |
| `API ...` | საიტზე დამატების შედეგი |
| `FAILED` | შეცდომა, traceback-ით |

მაგალითი:

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

კონკრეტული მიწისძვრის საძებნად: `grep ies2026rudf logs/event_scalert.log`.

ხელით გაშვება ტესტისთვის (scalert-ის გარეშე):

```
./scalert_event.py "manual test" 1 ies2026rudf 0
./scalert_event.py --dry-run ies2026rudf     # წყვეტს და წერს ლოგს, მაგრამ არ აგზავნის
```

## 9. კონფიგურაცია — `.env`

ყველა პაროლი და მისამართი მხოლოდ `.env`-შია (git-ში არ ემატება), კოდში არაფერი წერია.
`config.py` კითხულობს `.env`-ს და აწვდის დანარჩენ მოდულებს.

| ცვლადი | დანიშნულება |
|--------|-------------|
| `SC_DB_HOST`, `SC_DB_USER`, `SC_DB_PASSWORD`, `SC_DB_NAME` | SeisComP-ის ბაზა |
| `BORDERS_DB_HOST`, `BORDERS_DB_USER`, `BORDERS_DB_PASSWORD`, `BORDERS_DB_NAME` | საზღვრების ბაზა |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP |
| `RECIPIENTS_FILE` | მეილის მიმღებები, ნაგულისხმევად `recipients/email_recipients.json` (იხ. ნაწილი 10) |
| `SMS_RECIPIENTS_FILE` | SMS-ის მიმღებები, ნაგულისხმევად `recipients/sms_recipients.json` |
| `Recp_Exporter_API_URL`, `Recp_Exporter_API_KEY` | iesdata API, საიდანაც მიმღებები ახლდება |
| `Recp_Exporter_API_CA` | მხოლოდ self-signed სერტიფიკატის შემთხვევაში; ნაგულისხმევად სისტემის CA-ები |
| `Send_eq2api_API_URL`, `Send_eq2api_API_KEY` | iesdata API, სადაც გამოსაქვეყნებელი მიწისძვრები ემატება |
| `SEND_EQ2API` | `0` — მიწისძვრები საიტზე არ ემატება |
| `LOG_LEVEL` | `DEBUG`-ზე ლოგში ჩანს წესებში შესული მონაცემებიც |
| `SEND_EMAIL`, `SEND_SMS` | `0` — შესაბამისი არხი გამორთულია (ნაგულისხმევად ორივე ჩართულია) |
| `SMS_PROVIDERS` | SMS პროვაიდერების რიგი, `magti,smsoffice,gsm` |
| `MAGTI_USERNAME`, `MAGTI_PASSWORD`, `MAGTI_CLIENT_ID`, `MAGTI_SERVICE_ID` | Magti gateway |
| `SMSOFFICE_KEY`, `SMSOFFICE_SENDER`, `SMSOFFICE_BALANCE_WARNING` | smsoffice.ge |
| `GSM_SMS_URL`, `GSM_SMS_CODE` | GSM მოდემის სერვისი |
| `DRY_RUN` | `1` — არაფერი იგზავნება, მხოლოდ ლოგი |

## 10. მიმღებები

მიმღებები იმართება Notify-ის გვერდიდან (iesdata). `recipients/update_recipients.py`
API-დან ქმნის ორ ლოკალურ ფაილს (ორივე git-ში არ ემატება):

```
iesdata API  GET /api/recips/  (X-API-Key)
     │   {"items": [{username, is_staff, is_active,
     │               emails:  [{email, is_active}],
     │               numbers: [{phone_number, is_active}]}], "total": N}
     ▼
recipients/update_recipients.py      (cron-ით, პერიოდულად)
     │                      │
     ▼                      ▼
email_recipients.json    sms_recipients.json
(თითო მისამართი)         (თითო ნომერი)
     │
     ▼
send_notification/recipients.py      (ყოველ მეილისა და SMS-ის გაგზავნაზე)
```

| ფაილი | `.env` | ნიმუში |
|-------|--------|--------|
| `recipients/email_recipients.json` | `RECIPIENTS_FILE` | `recipients/email_recipients.example.json` |
| `recipients/sms_recipients.json` | `SMS_RECIPIENTS_FILE` | `recipients/sms_recipients.example.json` |

ფორმატი:

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

- ჩანაწერი აქტიურია მხოლოდ მაშინ, თუ აქტიურია **მიმღებიც და მისი მისამართი/ნომერიც**;
- `staff` ჯგუფს ეგზავნება მხოლოდ `is_staff: true`; `all`-ს — ყველა აქტიურს;
- ფაილი იკითხება ყოველ გაგზავნაზე, ამიტომ განახლება მაშინვე მოქმედებს.

`update_recipients.py`:

```
./recipients/update_recipients.py            # API-დან წაკითხვა და ორივე ფაილის განახლება
./recipients/update_recipients.py --dry-run  # მხოლოდ ნახვა, ფაილები არ იცვლება
```

- ფაილი იცვლება მხოლოდ წარმატებული პასუხის შემდეგ და ატომურად (ჯერ `.tmp`, მერე გადარქმევა);
- თუ API მიუწვდომელია, **ორივე ძველი ფაილი რჩება**; თუ რომელიმე სიაში არც ერთი აქტიური
  ჩანაწერი არ არის, **მხოლოდ ის ფაილი რჩება ძველი**, მეორე ჩვეულებრივად ახლდება
  (ორივე შემთხვევაში გამოსვლის კოდი `1`); ცარიელი სიის ჩასაწერად — `--allow-empty`;
- API სერვერს Let's Encrypt-ის სერტიფიკატი აქვს (2026-10-15-დან) და კავშირი სისტემის CA-ებით
  მოწმდება; `Recp_Exporter_API_CA` საჭიროა მხოლოდ self-signed სერტიფიკატის შემთხვევაში;
- ლოგი: `logs/update_recipients.log` — `UPDATED`, `UNCHANGED`, `FAILED`.

cron-ის მაგალითი (ყოველ 10 წუთში), `crontab -e`:

```
*/10 * * * * /home/sysop/Clone/Seiscomp_Scripts/scalert_event/recipients/update_recipients.py >/dev/null 2>&1
```

## 11. ფაილების სტრუქტურა

```
scalert_event/
├── scalert_event.py          შესვლის წერტილი (scalert იძახებს)
├── config.py                 .env-ის წაკითხვა
├── seiscomp_db.py            load_event(event_id) -> EventData
├── .env                      პაროლები (git-ში არა); ნიმუში — .env.example
├── requirements.txt          pymysql, pytest
├── recipients/
│   ├── update_recipients.py  API-დან ორივე ფაილის განახლება
│   ├── email_recipients.json მეილის მიმღებები (git-ში არა); ნიმუში — email_recipients.example.json
│   └── sms_recipients.json   SMS-ის მიმღებები (git-ში არა); ნიმუში — sms_recipients.example.json
├── venv/                     Python გარემო (git-ში არა)
├── automate_events/
│   ├── __init__.py
│   ├── automate_event.py     process_event, EventAssessment
│   ├── rules.py              ვის ეგზავნება და რატომ
│   ├── location.py           ქართული ლოკაციის ტექსტი
│   ├── acceleration.py       აჩქარების ფორმულა
│   ├── borders_db.py         ies_borders ბაზა
│   └── geo.py                მანძილი, მიმართულება, პოლიგონი
├── send_notification/
│   ├── message.py            თემა, მეილისა და SMS-ის ტექსტი
│   ├── recipients.py         მიმღებები (მეილები და ნომრები)
│   ├── mailer.py             SMTP
│   ├── ies_mail_sender.py    send_event_mail
│   └── ies_sms_sender.py     send_event_sms, SmsSender (magti → smsoffice → gsm)
├── send_eq2api/
│   ├── event_sender.py       send_event_api (SeisComP → საიტის ფორმატი)
│   └── send_eq2api.py        EventApiClient (iesdata API)
├── logs/                     event_scalert.log, update_recipients.log
└── tests/
```

## 12. ინსტალაცია და გაშვება

```
cd /home/sysop/Clone/Seiscomp_Scripts/scalert_event
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env                       # შეავსე პაროლები და API key-ები
chmod +x scalert_event.py recipients/update_recipients.py
./recipients/update_recipients.py          # მიმღებების პირველი ჩამოტვირთვა
./venv/bin/python -m pytest -q             # ტესტები (ბაზა და SMTP არ სჭირდება)
./scalert_event.py --dry-run <event_id>    # რეალური ბაზით, გაგზავნის გარეშე
```

`scalert_event.py`-ის shebang მიუთითებს `venv/bin/python`-ზე (აბსოლუტური მისამართით),
ამიტომ scalert-ს დამატებითი პარამეტრი არ სჭირდება. საქაღალდის გადატანისას shebang
უნდა შეიცვალოს.

ბოლოს scalert-ის კონფიგურაციაში (`scripts.event`, ნაწილი 2) მიეთითება სკრიპტი და
scalert გადაიტვირთება: `seiscomp restart scalert`. მიმღებების განახლებისთვის cron-ის
ჩანაწერი — ნაწილი 10.
