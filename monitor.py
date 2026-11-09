
#!/usr/bin/env python3
"""Treinmonitor Tiel 07:53 via Utrecht Centraal."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")
STATE = Path("monitor_state.json")

STATION = "Tl"
DEPARTURE = "07:53"
API_URL = (
    "https://gateway.apiportal.ns.nl/"
    "reisinformatie-api/api/v2/departures"
)


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(TZ)


def get_departures():
    params = urlencode({
        "station": STATION,
        "maxJourneys": 100,
    })
    request = Request(
        API_URL + "?" + params,
        headers={
            "Ocp-Apim-Subscription-Key":
                os.environ["NS_API_KEY"],
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=20) as response:
        data = json.load(response)

    departures = data.get("payload", {}).get(
        "departures", []
    )
    print("NS API bereikbaar:", len(departures))
    return departures


def find_train(departures, now):
    for dep in departures:
        planned = dep.get("plannedDateTime")
        if not planned:
            continue

        dt = parse_time(planned)

        if dt.date() != now.date():
            continue

        if dt.strftime("%H:%M") != DEPARTURE:
            continue

        direction = str(
            dep.get("direction") or ""
        ).lower()

        stations = dep.get("routeStations") or []
        route = " ".join(
            str(station.get("mediumName") or "")
            for station in stations
            if isinstance(station, dict)
        ).lower()

        if (
            "utrecht" in direction
            or "utrecht" in route
            or "8400621" in str(stations)
        ):
            return dep

    return None


def send_notification(title, body):
    topic = os.environ["NTFY_TOPIC"]
    request = Request(
        "https://ntfy.sh/" + topic,
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "high",
            "Tags": "train,warning",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        print("Push verzonden:", response.status)


def load_state():
    if STATE.exists():
        try:
            return json.loads(
                STATE.read_text(encoding="utf-8")
            )
        except (ValueError, OSError):
            pass
    return {}


def save_state(state):
    STATE.write_text(
        json.dumps(state),
        encoding="utf-8",
    )


def check_train(departures, now, notify=True):
    dep = find_train(departures, now)

    if dep is None:
        print("Trein 07:53 niet gevonden.")
        print("Geen melding: uitval niet bevestigd.")
        return

    planned = parse_time(dep["plannedDateTime"])
    expected = parse_time(
        dep.get("expectedDateTime")
        or dep.get("actualDateTime")
        or dep["plannedDateTime"]
    )

    delay = max(
        0,
        round(
            (expected - planned).total_seconds() / 60
        ),
    )
    cancelled = dep.get("cancelled") is True

    status = (
        "cancelled" if cancelled
        else f"delay:{delay}" if delay >= 3
        else "ok"
    )

    print("Trein gevonden:", DEPARTURE)
    print("Richting:", dep.get("direction"))
    print("Verwacht vertrek:", expected)
    print("Vertraging:", delay, "minuten")
    print("Uitgevallen:", cancelled)
    print("Status:", status)

    if not notify:
        print("Testmodus: geen push verstuurd.")
        return

    state = load_state()
    key = now.date().isoformat()
    previous = state.get(key)

    if status == previous:
        print("Status ongewijzigd; geen melding.")
        return

    if status == "ok":
        print("Geen vertraging van 3+ minuten.")
    elif cancelled:
        send_notification(
            "Trein Tiel 07:53 uitgevallen",
            "NS meldt dat de trein is uitgevallen. "
            "Controleer je reis.",
        )
    else:
        send_notification(
            f"Trein 07:53: {delay} min vertraging",
            f"Verwacht vertrek uit Tiel: "
            f"{expected:%H:%M}.",
        )

    # Bewaar alleen de status van vandaag.
    save_state({key: status})


def test_matching():
    now = datetime.now(TZ)
    sample = {
        "plannedDateTime":
            now.strftime("%Y-%m-%dT07:53:00%z"),
        "direction": "Den Haag Centraal",
        "routeStations": [
            {
                "uicCode": "8400621",
                "mediumName": "Utrecht C.",
            }
        ],
    }
    assert find_train([sample], now) == sample
    print("Treinherkenning geslaagd.")
    print("07:53 via Utrecht C. wordt herkend.")


def main():
    now = datetime.now(TZ)
    mode = sys.argv[1] if len(sys.argv) > 1 else "monitor"

    print("Lokale tijd:", now.isoformat())
    print("Modus:", mode)

    if mode == "test-match":
        test_matching()
        return

    if mode == "test-push":
        send_notification(
            "Test treinmonitor",
            "GitHub kan meldingen versturen!",
        )
        return

    if mode == "test-api":
        departures = get_departures()
        for dep in departures:
            print(
                dep.get("plannedDateTime"),
                dep.get("direction"),
                dep.get("routeStations"),
            )
        return

    if mode == "test-live":
        check_train(get_departures(), now, notify=False)
        return

    if mode != "monitor":
        raise ValueError("Onbekende modus: " + mode)

    if now.weekday() != 0 or not (
        "07:05" <= now.strftime("%H:%M") <= "07:53"
    ):
        print("Buiten controleperiode; overgeslagen.")
        return

    check_train(get_departures(), now)


if __name__ == "__main__":
    main()
