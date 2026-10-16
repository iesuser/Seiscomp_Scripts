# scalert_event — გამართვის ინსტრუქცია

ეს ინსტრუქცია აღწერს, როგორ დავაყენოთ და ჩავრთოთ `scalert_event`: რა სჭირდება, რატომ
ვიყენებთ თითოეულ ნაწილს და როგორ შევამოწმოთ, რომ ყველაფერი მუშაობს.

როგორ მუშაობს სისტემა შიგნით (წესები, ლოკაცია, ლოგის ყველა ჩანაწერი, API), აღწერილია
სრულ დოკუმენტაციაში: [docs/scalert_event_ka.md](docs/scalert_event_ka.md)
([English](docs/scalert_event_en.md); HTML და PDF ვერსიები იმავე საქაღალდეშია).

## შინაარსი

1. [რას აკეთებს](#1-რას-აკეთებს)
2. [რა სჭირდება და რატომ](#2-რა-სჭირდება-და-რატომ)
3. [ინსტალაცია](#3-ინსტალაცია)
4. [`.env`-ის შევსება](#4-env-ის-შევსება)
5. [შემოწმება ჩართვამდე](#5-შემოწმება-ჩართვამდე)
6. [scalert-ში ჩართვა](#6-scalert-ში-ჩართვა)
7. [მიმღებების ავტომატური განახლება (cron)](#7-მიმღებების-ავტომატური-განახლება-cron)
8. [ყოველდღიური მუშაობა](#8-ყოველდღიური-მუშაობა)
9. [პრობლემები და გადაჭრა](#9-პრობლემები-და-გადაჭრა)
10. [განახლება და გადატანა](#10-განახლება-და-გადატანა)
11. [დოკუმენტაციის განახლება](#11-დოკუმენტაციის-განახლება)

## 1. რას აკეთებს

SeisComP-ში მიწისძვრის გაჩენისას ან განახლებისას `scalert` უშვებს `scalert_event.py`-ს.
სკრიპტი:

1. SeisComP-ის ბაზიდან კითხულობს მიწისძვრის პარამეტრებს;
2. წესების მიხედვით წყვეტს, ვის ეგზავნება: ყველას, მხოლოდ თანამშრომლებს, ან არავის;
3. აგზავნის მეილს და SMS-ს;
4. მიწისძვრას ამატებს iesdata საიტზე, ხოლო თუ ყველას ეგზავნება, აქვეყნებს WordPress-ზეც;
5. ყველაფერს წერს ლოგში `logs/event_scalert.log`.

## 2. რა სჭირდება და რატომ

### 2.1 სერვისები

| რა | რისთვის | რატომ ასე |
|----|---------|-----------|
| **SeisComP `scalert`** | იძახებს სკრიპტს ყოველ მიწისძვრაზე | SeisComP-ის სტანდარტული მექანიზმია; ცალკე დემონი არ გვჭირდება |
| **SeisComP-ის MySQL ბაზა** (`seiscomp`) | მიწისძვრის დრო, კოორდინატები, სიღრმე, მაგნიტუდები | scalert-ის არგუმენტებში ყველაფერი არ არის; ბაზა ერთადერთი სანდო წყაროა |
| **`ies_borders` MySQL ბაზა** | საქართველოს და თბილისის საზღვრები, ქალაქები, დასახლებები | წესებს სჭირდება „საქართველოშია?“, „თბილისშია?“, „რამდენი კმ-ია?“; ლოკაციის ტექსტს — სახელები ორ ენაზე |
| **SMTP სერვერი** | მეილის გაგზავნა | — |
| **SMS პროვაიდერები**: Magti, smsoffice.ge, GSM მოდემი | SMS | სამი პროვაიდერი ჯაჭვად: თუ ერთი ვერ აგზავნის, ნომერი შემდეგზე გადადის |
| **iesdata API** (`https://iesdata.iliauni.edu.ge:3030`) | მიმღებების სია; მიწისძვრების დამატება; WordPress-ზე გამოქვეყნება | მიმღებები ერთ ადგილას იმართება (Notify), მიწისძვრები კი საიტზე ავტომატურად ჩნდება |
| **cron** | მიმღებების ფაილების განახლება ყოველ 10 წუთში | გაგზავნა API-ზე არ არის დამოკიდებული: თუ API მიუწვდომელია, ბოლო ფაილი მაინც არსებობს |

### 2.2 API გასაღებები

iesdata-ზე სამი სერვისის გასაღები გამოიყენება. თითოეულს მხოლოდ საჭირო უფლება აქვს,
რომ ერთი გასაღების გაჟონვამ ყველაფერზე წვდომა არ მისცეს:

| `.env` | ვინ იყენებს | საჭირო უფლება |
|--------|-------------|----------------|
| `Recp_Exporter_API_KEY` | `recipients/update_recipients.py` | მიმღებების წაკითხვა (`GET /api/recips/`) |
| `Send_eq2api_API_KEY` | `send_eq2api` — მიწისძვრის დამატება და განახლება | `can_event_edit` |
| `SeisComp_Publisher_API_KEY` | `send_eq2api` — WordPress-ზე გამოქვეყნება და ჩამოხსნა | `can_event_publish` |

### 2.3 Python და ბიბლიოთეკები

| რა | რისთვის | რატომ |
|----|---------|-------|
| **Python 3.14**, `venv/` საქაღალდეში | მთელი კოდი | ცალკე გარემო: სისტემის ან SeisComP-ის Python-ის განახლება სკრიპტს არ აფუჭებს |
| **`pymysql`** | SeisComP-ის და `ies_borders` ბაზები | მთლიანად Python-შია, C ბიბლიოთეკები და კომპილაცია არ სჭირდება |
| **`requests`** | iesdata API (`send_eq2api`) | session, timeout, JSON და შეცდომების მარტივი დამუშავება |
| **`certifi`** | `requests`-ის CA სერტიფიკატები | სერვერს Let's Encrypt-ის სერტიფიკატი აქვს; certifi-ს განახლებული სია მას ამოწმებს |
| **`pytest`** | ტესტები | ტესტებს ბაზა, SMTP და ქსელი არ სჭირდება |
| სტანდარტული `smtplib`, `urllib`, `ssl` | მეილი, SMS, მიმღებების API | დამატებითი ბიბლიოთეკა არ სჭირდება; სისტემის CA-ებს იყენებს |

ყველა ვერსია `requirements.txt`-შია.

### 2.4 რატომ `.env`

ყველა პაროლი და გასაღები მხოლოდ `.env`-შია, რომელიც git-ში არ ემატება
(`.gitignore`). კოდში და დოკუმენტაციაში საიდუმლო არაფერი წერია. ნიმუში ცარიელი
მნიშვნელობებით არის `.env.example`.

## 3. ინსტალაცია

```
cd /home/sysop/Clone/Seiscomp_Scripts/scalert_event
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
chmod +x scalert_event.py recipients/update_recipients.py send_eq2api/send_eq2api.py
mkdir -p logs
```

- `chmod 600 .env` — `.env`-ს მხოლოდ მფლობელი კითხულობს, რადგან მასში პაროლებია;
- სკრიპტების პირველი ხაზი (shebang) მიუთითებს `venv/bin/python`-ზე აბსოლუტური
  მისამართით. ამიტომ scalert-ს და cron-ს არც `source venv/bin/activate` სჭირდებათ, არც
  დამატებითი პარამეტრი.

## 4. `.env`-ის შევსება

შეავსე `.env` ქვემოთ მოცემული რიგით. სრული სია ნაგულისხმევი მნიშვნელობებით:
[docs/scalert_event_ka.md, ნაწილი 10](docs/scalert_event_ka.md#10-კონფიგურაცია-env).

| ჯგუფი | ცვლადები | რჩევა |
|-------|----------|-------|
| SeisComP-ის ბაზა | `SC_DB_HOST`, `SC_DB_USER`, `SC_DB_PASSWORD`, `SC_DB_NAME` | იგივე ბაზა, რომელშიც `scmaster` წერს; საკმარისია მხოლოდ `SELECT` უფლება |
| საზღვრების ბაზა | `BORDERS_DB_HOST`, `BORDERS_DB_USER`, `BORDERS_DB_PASSWORD`, `BORDERS_DB_NAME` | მხოლოდ `SELECT` უფლება; პაროლი სავალდებულოა |
| მეილი | `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | პორტი 587, STARTTLS |
| SMS | `MAGTI_*`, `SMSOFFICE_KEY`, `GSM_SMS_CODE` | ცარიელი პროვაიდერი უბრალოდ გამოიტოვება |
| მიმღებები | `Recp_Exporter_API_URL`, `Recp_Exporter_API_KEY` | — |
| საიტი | `Send_eq2api_API_URL`, `Send_eq2api_API_KEY`, `SeisComp_Publisher_API_KEY` | იხ. ნაწილი 2.2 |
| არხების ჩართვა | `SEND_EMAIL`, `SEND_SMS`, `SEND_EQ2API` | `0` გამორთავს; ნაგულისხმევად ყველა ჩართულია |
| უსაფრთხო რეჟიმი | `DRY_RUN` | `1` — ყველაფერი ითვლება და ლოგში იწერება, მაგრამ არაფერი იგზავნება |

**სერტიფიკატები.** `*_API_CA` ცვლადები **არ** შეავსო. iesdata-ს Let's Encrypt-ის
სერტიფიკატი აქვს (2026-10-15-დან) და ის სისტემის CA-ებით და `certifi`-ით მოწმდება.
`Recp_Exporter_API_CA` და `Send_eq2api_API_CA` საჭიროა მხოლოდ მაშინ, თუ სერვერი
ისევ self-signed სერტიფიკატზე გადავა.

## 5. შემოწმება ჩართვამდე

ყველა ნაბიჯი უსაფრთხოა: არაფერს აგზავნის და საიტზე არაფერს ცვლის.

```
# 1. ტესტები (ბაზა, SMTP და ქსელი არ სჭირდება)
./venv/bin/python -m pytest -q

# 2. მიმღებების API: ნახვა, ფაილები არ იცვლება
./recipients/update_recipients.py --dry-run

# 3. მიმღებების პირველი ჩამოტვირთვა
./recipients/update_recipients.py

# 4. საიტის API: მხოლოდ კითხულობს, არის თუ არა მიწისძვრა საიტზე
./send_eq2api/send_eq2api.py <event_id>

# 5. მთელი გზა რეალური ბაზით, გაგზავნის გარეშე
./scalert_event.py --dry-run <event_id>
tail -20 logs/event_scalert.log
```

რას უნდა ელოდო:

| ნაბიჯი | კარგი შედეგი |
|--------|--------------|
| 1 | `... passed`, შეცდომის გარეშე |
| 2–3 | მიმღებების რაოდენობა; ლოგში `UPDATED` ან `UNCHANGED` |
| 4 | `... is not on the site.` ან მიწისძვრის მონაცემები საიტიდან; `HTTP 401`/`403` ნიშნავს, რომ გასაღები ან უფლება არასწორია |
| 5 | ლოგში `RECEIVED`, `INPUT`, `DECISION` და ბოლოს `DONE ... dry_run=True` ან `DECISION ... NOT SENT` |

`<event_id>`-ად აიღე ბოლო რეალური მიწისძვრა, მაგ. scolv-იდან ან ბაზიდან:

```
mysql -u sysop -p seiscomp -e "SELECT publicID FROM PublicObject p JOIN Event e ON e._oid=p._oid ORDER BY e._oid DESC LIMIT 5"
```

## 6. scalert-ში ჩართვა

`~/seiscomp/etc/scalert.cfg` (ან `scconfig` → Modules → scalert):

```
scripts.event = /home/sysop/Clone/Seiscomp_Scripts/scalert_event/scalert_event.py
```

შემდეგ:

```
seiscomp update-config scalert
seiscomp restart scalert
```

- scalert სკრიპტს იმავე მომხმარებლით უშვებს, რომლითაც თავად მუშაობს (`sysop`). ამ
  მომხმარებელს უნდა ჰქონდეს `.env`-ის წაკითხვის და `logs/`-ში ჩაწერის უფლება;
- `scripts.event`-ს არგუმენტები არ სჭირდება: scalert თავად გადასცემს `event_id`-ს;
- პირველი რეალური მიწისძვრის შემდეგ შეამოწმე `logs/event_scalert.log`.

## 7. მიმღებების ავტომატური განახლება (cron)

`crontab -e`:

```
*/10 * * * * /home/sysop/Clone/Seiscomp_Scripts/scalert_event/recipients/update_recipients.py >/dev/null 2>&1
```

რატომ: მიმღებები Notify-ის გვერდზე იცვლება. ფაილი ყოველ 10 წუთში ახლდება, ხოლო
გაგზავნისას ლოკალური ფაილი იკითხება. ამიტომ API-ის დროებითი გათიშვა გაგზავნას არ
აჩერებს. შედეგი იწერება `logs/update_recipients.log`-ში.

## 8. ყოველდღიური მუშაობა

```
tail -f logs/event_scalert.log                       # მიმდინარე
grep "event_id=ies2026rudf" logs/event_scalert.log   # ერთი მიწისძვრის ისტორია
grep " ERROR " logs/event_scalert.log                # მხოლოდ პრობლემები
```

ყოველი გაშვება ერთ-ერთი ხაზით მთავრდება:

| ბოლო ხაზი | ნიშნავს |
|-----------|---------|
| `INFO DONE ... mail=sent sms=sent api=sent` | ყველაფერი გაიგზავნა |
| `ERROR DONE ... api=failed` | ერთი ან მეტი არხი ჩავარდა; მიზეზი ზედა ხაზშია (`API FAILED ...`) |
| `INFO DECISION ... NOT SENT` | წესებით არავის ეგზავნება; მიზეზი იქვე წერია |
| `INFO SKIPPED` | არარეალური მიწისძვრა, ან მაგნიტუდა ჯერ არ აქვს |
| `ERROR FAILED` | ვერ დამუშავდა, მაგ. მიწისძვრა ბაზაში ვერ მოიძებნა |

არხის დროებით გამოსართავად (მაგ. SMS პროვაიდერის პრობლემისას) `.env`-ში ჩაწერე
`SEND_SMS=0`. გადატვირთვა არ სჭირდება: `.env` ყოველ გაშვებაზე იკითხება.

## 9. პრობლემები და გადაჭრა

| ლოგში | მიზეზი | რა ვქნათ |
|-------|--------|----------|
| `FAILED event_id=...: event ... not found` | მიწისძვრა ამ ბაზაში არ არის, ან `scdb` ძალიან აგვიანებს | შეამოწმე `SC_DB_*`; საჭიროებისას გაზარდე `SC_DB_RETRIES` |
| `WAITING ...` რამდენჯერმე, მერე წარმატება | ნორმალურია: `scdb` ჯერ წერდა | არაფერი |
| `CERTIFICATE_VERIFY_FAILED` | სერვერის სერტიფიკატი ვერ მოწმდება | `./venv/bin/pip install -U certifi`; თუ `*_API_CA` წერია `.env`-ში და სერვერს Let's Encrypt აქვს, წაშალე |
| `HTTP 401: API key არასწორია` | გასაღები არასწორია ან გაუქმდა | შეამოწმე შესაბამისი `*_API_KEY` |
| `HTTP 403: სერვისს არ აქვს საჭირო უფლება` | სერვისს უფლება აკლია | iesdata-ზე მიეცი `can_event_edit` / `can_event_publish` (ნაწილი 2.2) |
| `SeisComp_Publisher_API_KEY is not set` | `.env`-ში გასაღები არ არის | ჩაწერე გასაღები; მანამდე მიწისძვრა საიტზე ემატება, მაგრამ არ ქვეყნდება |
| `API MAGNITUDES SKIPPED ...: Mwp` | საიტი ამ მაგნიტუდას არ იცნობს | თუ საიტზე დაემატა, ჩაამატე `SITE_MAGNITUDE_CODES`-ში (`send_eq2api/send_eq2api.py`) |
| `API NOT SENT ...: no magnitude the site knows` | არც ერთი მაგნიტუდა საიტის კოდი არ არის | იგივე |
| `MAIL FAILED` | SMTP-ის შეცდომა; traceback ზემოთაა | შეამოწმე `MAIL_*`, პაროლი, პორტი |
| `MAIL NOT SENT` / `SMS NOT SENT` | ჯგუფში აქტიური მიმღები არ არის | შეამოწმე Notify და `logs/update_recipients.log` |
| `SMS FAILED` | ზოგ ნომერზე ვერც ერთმა პროვაიდერმა ვერ გაგზავნა | ზედა ხაზებში ჩანს თითო პროვაიდერის პასუხი |
| `SMS BALANCE LOW` | smsoffice-ზე ცოტა SMS დარჩა | შეავსე ბალანსი |
| `BORDERS_DB_PASSWORD is not set` | საზღვრების ბაზის პაროლი არ არის | ჩაწერე `.env`-ში |
| `Access denied` / `Can't connect to MySQL` | ბაზის მომხმარებელი, პაროლი ან ჰოსტი | შეამოწმე `mysql -u ... -p`-ით |
| ლოგი საერთოდ არ ჩნდება | scalert სკრიპტს არ იძახებს | შეამოწმე `scripts.event`, `chmod +x` და `seiscomp status scalert` |
| ლოკაციის ინგლისური სახელი არასწორია | ბაზაში ასე წერია | გაასწორე `ies_borders` ბაზაში (`name_en`) |

## 10. განახლება და გადატანა

კოდის განახლება:

```
git pull
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m pytest -q
```

თუ `.env.example`-ში ახალი ცვლადი გამოჩნდა, ის `.env`-შიც უნდა ჩაემატოს.

**სხვა საქაღალდეში ან სერვერზე გადატანისას:**

1. შეცვალე shebang (პირველი ხაზი) სამ ფაილში: `scalert_event.py`,
   `recipients/update_recipients.py`, `send_eq2api/send_eq2api.py`;
2. თავიდან შექმენი `venv` (ნაწილი 3), რადგან venv სხვა მისამართზე არ მუშაობს;
3. გადაიტანე `.env` უსაფრთხო გზით (არა git-ით და არა ჩატით);
4. შეცვალე მისამართი `scripts.event`-ში და cron-ში.

## 11. დოკუმენტაციის განახლება

სრული დოკუმენტაცია `docs/`-შია სამ ფორმატში. წყაროა `.md` ფაილი, HTML და PDF მისგან
იქმნება:

| ფაილი | რა არის |
|-------|---------|
| `docs/scalert_event_ka.md`, `.html`, `.pdf` | სრული დოკუმენტაცია, ქართულად |
| `docs/scalert_event_en.md`, `.html`, `.pdf` | სრული დოკუმენტაცია, ინგლისურად |
| `docs/setup_ka.html`, `.pdf` | ეს ინსტრუქცია |
| `docs/index.html` | ყველა ფაილის სია |

`.md`-ის შეცვლის შემდეგ:

```
./venv/bin/pip install -r docs/requirements.txt    # ერთხელ
./venv/bin/python docs/build_docs.py
```

PDF-ისთვის საჭიროა Google Chrome ან Chromium.
