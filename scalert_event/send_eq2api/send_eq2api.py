import math
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BASE_DIR, load_env_file  # noqa: E402

load_env_file()

# კონფიგურაცია: key და მისამართი env ცვლადებიდან იკითხება, კოდში არაფერი წერია
BASE_URL = os.getenv("Send_eq2api_API_URL", "https://iesdata.iliauni.edu.ge:3030/").rstrip("/")
API_KEY = os.getenv("Send_eq2api_API_KEY")
TIMEOUT = float(os.getenv("Send_eq2api_API_TIMEOUT") or 20)  # წამი; ყველა HTTP მოთხოვნას აქვს timeout

# სერტიფიკატი ჩვეულებრივი CA-ებით მოწმდება; Send_eq2api_API_CA საჭიროა მხოლოდ self-signed სერვერისთვის
CA_FILE = os.getenv("Send_eq2api_API_CA")
VERIFY = str(BASE_DIR / CA_FILE) if CA_FILE else True

# ველები, რომლებიც აუცილებლად უნდა იყოს მითითებული
REQUIRED = ("seiscomp_oid", "origin_time", "latitude", "longitude")

# ტექსტური ველები და მათი მაქსიმალური სიგრძე
MAX_LEN = {
    "seiscomp_oid": 100,
    "iesdata_id": 100,
    "area": 20,
    "location_ge": 500,
    "location_en": 500,
}

# დასაშვები გასაღებების სრული სია; სხვა ნებისმიერი (მაგ. ბეჭდვის შეცდომა) უარყოფილია
ALLOWED_KEYS = {*REQUIRED, *MAX_LEN, "depth", "magnitudes", "is_automatic"}

# HTTP სტატუსები, რომლებზეც API-ის message-ის ნაცვლად ჩვენი ტექსტი ჩანს
HTTP_ERRORS = {
    401: "API key არასწორია",
    403: "სერვისს არ აქვს can_event_edit უფლება",
}


class ApiError(RuntimeError):
    """API-მ შეცდომა დააბრუნა ან მიუწვდომელია."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status  # HTTP სტატუსი (ქსელის შეცდომისას None)


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    """უგზავნის მოთხოვნას API-ს და აბრუნებს პასუხის JSON-ს; შეცდომაზე ApiError."""
    if not API_KEY:
        raise ApiError("API_KEY is not set.")

    # ქსელის შეცდომა ან timeout -> ApiError
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            json=payload,
            headers={"X-API-Key": API_KEY},
            timeout=TIMEOUT,
            verify=VERIFY,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach API: {exc}") from exc

    # პასუხი ყოველთვის JSON არ არის (მაგ. 500-ზე HTML), ამ შემთხვევაში ცარიელი dict
    try:
        data = response.json()
    except ValueError:
        data = {}

    # წარუმატებელი სტატუსი: ჯერ ჩვენი ტექსტი (401/403), მერე API-ის message, მერე default
    if not response.ok:
        message = (
            HTTP_ERRORS.get(response.status_code)
            or (data.get("message") if isinstance(data, dict) else None)
            or "Unknown API error"
        )
        raise ApiError(
            f"{method} {path} failed with HTTP {response.status_code}: {message}",
            response.status_code,
        )
    return data


def _to_float(value, name):
    """გადაჰყავს მნიშვნელობა float-ში; უარყოფს bool-ს, nan-ს და inf-ს."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: {value}") from None
    # float(True) == 1.0, float("nan") და float("inf") შეცდომას არ იძლევა,
    # მაგრამ მიწისძვრის მონაცემად არასწორია
    if isinstance(value, bool) or not math.isfinite(result):
        raise ValueError(f"Invalid {name}: {value}")
    return result


def _validate_event(event: dict) -> None:
    """ამოწმებს event dict-ს; არასწორზე ValueError. შემავალ dict-ს არ ცვლის."""
    if not isinstance(event, dict):
        raise ValueError("Event must be a dict.")

    # უცნობი გასაღებები
    unknown_keys = event.keys() - ALLOWED_KEYS
    if unknown_keys:
        raise ValueError(f"Unknown event key(s): {', '.join(sorted(unknown_keys))}")

    # სავალდებულო ველები: უნდა არსებობდეს და არ იყოს None ან ცარიელი
    for key in REQUIRED:
        if event.get(key) is None or event.get(key) == "":
            raise ValueError(f"{key} is required.")

    # ტექსტური ველები: თუ მითითებულია, უნდა იყოს სტრიქონი და არ აღემატებოდეს მაქს. სიგრძეს
    # (not isinstance პირველია, რომ რიცხვზე len() არ გამოიძახოს)
    for key, max_len in MAX_LEN.items():
        value = event.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > max_len):
            raise ValueError(f"{key} must be a string of at most {max_len} characters.")

    # მაგნიტუდები: არაცარიელი dict, ყველა მნიშვნელობა რიცხვი
    magnitudes = event.get("magnitudes")
    if not isinstance(magnitudes, dict) or not magnitudes:
        raise ValueError("Event must have at least one magnitude.")

    for code, value in magnitudes.items():
        _to_float(value, f"magnitude {code}")

    # დრო: ISO ფორმატი (YYYY-MM-DD HH:MM:SS ან YYYY-MM-DDTHH:MM:SS)
    try:
        datetime.fromisoformat(event["origin_time"])
    except (TypeError, ValueError):
        raise ValueError("Invalid origin_time.") from None

    # კოორდინატები: რიცხვი და დიაპაზონში (-limit ... limit)
    for key, limit in (("latitude", 90), ("longitude", 180)):
        if abs(_to_float(event[key], key)) > limit:
            raise ValueError(f"{key} must be between {-limit} and {limit}.")

    # სიღრმე: არასავალდებულო, მაგრამ თუ არის, უნდა იყოს რიცხვი
    if event.get("depth") is not None:
        _to_float(event["depth"], "depth")

    # is_automatic: თუ მითითებულია, უნდა იყოს bool (არა სტრიქონი "True")
    if not isinstance(event.get("is_automatic", False), bool):
        raise ValueError("is_automatic must be a bool.")

def find_event_by_oid(seiscomp_oid) -> dict | None:
    """ეძებს მიწისძვრას seiscomp_oid-ით; აბრუნებს მიწისძვრას ან None-ს."""
    data = _request(
        "POST",
        "/api/seismic_events/filter",
        {"seiscomp_oid": seiscomp_oid},
    )

    # API ნაწილობრივ დამთხვევასაც აბრუნებს ("abc" იპოვის "abc123"-საც),
    # ამიტომ ვიღებთ მხოლოდ ზუსტ დამთხვევას
    for item in data.get("items", []):
        if item.get("seiscomp_oid") == seiscomp_oid:
            return item

    return None


def add_event(event: dict) -> dict:
    """ამატებს მიწისძვრას მაგნიტუდებით, ან განაახლებს, თუ seiscomp_oid უკვე არსებობს.

    აბრუნებს {"id": ..., "created": True/False}.
    ValueError: არასწორი მონაცემები (API-ს არაფერი ეგზავნება).
    ApiError: API-მ შეცდომა დააბრუნა ან მიუწვდომელია.
    """
    # 1. შემოწმება: არასწორზე ValueError და API-ს ჯერ არაფერი ეგზავნება
    _validate_event(event)

    # 2. ორად გაყოფა (შემავალი dict არ იცვლება, ახალი dict-ები ვაგებთ):
    #    მიწისძვრის payload: magnitudes-ის და None მნიშვნელობების გარეშე
    event_payload = {
        key: value
        for key, value in event.items()
        if key != "magnitudes" and value is not None
    }

    #    მაგნიტუდები ცალკე, მნიშვნელობები float-ად
    magnitudes = {
        code: _to_float(value, f"magnitude {code}")
        for code, value in event["magnitudes"].items()
    }

    # 3. არსებობს თუ არა ეს მიწისძვრა უკვე
    existing = find_event_by_oid(event["seiscomp_oid"])

    # 4ა. ახალი მიწისძვრა: შექმნა + მაგნიტუდები, "ყველაფერი ან არაფერი"
    if existing is None:
        data = _request(
            "POST",
            "/api/seismic_events/",
            event_payload,
        )
        event_id = data["event"]["id"]

        try:
            for code, value in magnitudes.items():
                _request(
                    "POST",
                    f"/api/seismic_events/{event_id}/magnitudes",
                    {
                        "magnitude_code": code,
                        "value": value,
                    },
                )

        except ApiError as exc:
            # რომელიმე მაგნიტუდა ვერ დაემატა -> rollback:
            # შექმნილ მიწისძვრას ვშლით, რომ საიტზე მაგნიტუდის გარეშე არ დარჩეს
            # (code აქ ის მაგნიტუდაა, რომელზეც ციკლი გაჩერდა)
            try:
                _request(
                    "DELETE",
                    f"/api/seismic_events/{event_id}",
                )
            except ApiError as delete_exc:
                # წაშლაც ვერ მოხერხდა: მომხმარებელმა უნდა იცოდეს, რომ ხელით უნდა წაშალოს
                raise ApiError(
                    f"Event was not added: magnitude {code} failed: {exc}; "
                    f"rollback failed: {delete_exc}. "
                    f"Earthquake #{event_id} was left without magnitude "
                    f"and must be deleted manually."
                ) from delete_exc

            # rollback წარმატებულია, მაინც ვაგდებთ შეცდომას
            raise ApiError(
                f"Event was not added: magnitude {code} failed: {exc}"
            ) from exc

        return {"id": event_id, "created": True}

    # 4ბ. არსებული მიწისძვრა: განახლება
    else:
        event_id = existing["id"]

        _request(
            "PUT",
            f"/api/seismic_events/{event_id}",
            event_payload,
        )

        # არსებული მაგნიტუდები: კოდი (დიდი ასოებით) -> ჩანაწერი.
        # ჩანაწერის id გვჭირდება PUT-ისთვის, კოდი კი რეგისტრის გარეშე შესადარებლად
        existing_magnitudes = existing.get("magnitudes", [])
        existing_by_code = {
            item["magnitude"]["code"].upper(): item
            for item in existing_magnitudes
        }

        # თითო მაგნიტუდას ცალ-ცალკე ვცდით, რომ ერთის ჩავარდნამ დანარჩენები არ შეაჩეროს;
        # ჩავარდნილებს ვაგროვებთ და ბოლოს ერთად ვაცხადებთ.
        # საიტზე არსებულ მაგნიტუდებს, რომლებიც ახალ dict-ში არ არის, არ ვშლით
        failed = []
        for code, value in magnitudes.items():
            existing_magnitude = existing_by_code.get(code.upper())

            try:
                if existing_magnitude:
                    # ეს ტიპი უკვე აქვს -> მნიშვნელობას ვანახლებთ
                    _request(
                        "PUT",
                        f"/api/seismic_events/magnitudes/{existing_magnitude['id']}",
                        {"value": value},
                    )
                else:
                    # ეს ტიპი ჯერ არ აქვს -> ვამატებთ
                    _request(
                        "POST",
                        f"/api/seismic_events/{event_id}/magnitudes",
                        {
                            "magnitude_code": code,
                            "value": value,
                        },
                    )
            except ApiError as exc:
                failed.append(f"{code}: {exc}")

        # განახლებისას rollback არ არის (მიწისძვრა უკვე არსებობდა), მხოლოდ ვაცხადებთ, რა ჩავარდა
        if failed:
            raise ApiError(
                f"Event #{event_id} magnitude update failed: {'; '.join(failed)}"
            )

        return {"id": event_id, "created": False}


if __name__ == "__main__":
    # ხელით ტესტი: გაეშვება მხოლოდ პირდაპირ გაშვებისას (python3 post_event.py), import-ზე არა
    test_event = {
        "iesdata_id": None,
        "seiscomp_oid": "ies2026demo1",
        "origin_time": "2026-09-30 14:25:10",
        "latitude": 41.72,
        "longitude": 44.79,
        "depth": 12,
        "magnitudes": {"ML": 3.4, "MW": 3.2},
        "location_ge": "თბილისიდან 15 კმ ჩრდილო-აღმოსავლეთით",
        "location_en": "15 km NE of Tbilisi",
        "is_automatic": False,
        "area": "local",
    }

    try:
        result = add_event(test_event)
        print("Event:", result["id"], "created" if result["created"] else "updated")

    except (ApiError, ValueError) as exc:
        print(f"Error: {exc}")