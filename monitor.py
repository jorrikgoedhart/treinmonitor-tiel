
#!/usr/bin/env python3
"""Treinmonitor: Tiel 07:53, iedere maandag."""

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


def get_json(url, headers):
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def send_notification(topic, title, body):
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
        print("ntfy response:", response.status)


def get_departures():
    api_key = os.environ["NS_API_KEY"]
    params = urlencode({
        "station": STATION,
        "maxJourneys": 100,
    })
    data = get_json(
        API_URL + "?" + params,
        {
            "Ocp-Apim-Subscription-Key": api_key,
            "Accept": "application/json",
        },
    )
    departures = data.get("payload", {}).get("departures", [])
    print("NS API bereikbaar. Vertrekken:", len(departures))
    return departures


def find_train(departures, now):
    matches = []

    for dep in departures:
        planned = dep.get("plannedDateTime")
        if not planned:
            continue

        dt = datetime.fromisoformat(
            planned.replace("Z", "+00:00")
        ).astimezone(TZ)

        if dt.date() != now.date():
            continue

        if dt.strftime("%H:%M") != DEPARTURE:
            continue

        direction = str(dep.get("direction") or "").lower()
        route = str(dep.get("routeStations") or "").lower()

        if "utrecht" not in direction and "utrecht" not in route:
            continue

        matches.append(dep)

    return matches[0] if matches else None


def check_train(departures, now):
    dep = find_train(departures, now)

    if dep is None:
        print("Geen passende trein gevonden.")
        print("Dit betekent niet automatisch dat de trein uitvalt.")
        return

    planned = datetime.fromisoformat(
        dep["plannedDateTime"].replace("Z", "+00:00")
    )
    actual = datetime.fromisoformat(
        (dep.get("actualDateTime") or dep["plannedDateTime"])
        .replace("Z", "+00:00")
    )

    delay = max(
        0,
        round((actual - planned).total_seconds() / 60)
    )
    cancelled = bool(dep.get("cancelled"))

    status = (
        "cancelled" if cancelled
        else f"delay:{delay}" if delay >= 3
        else "ok"
    )

    print("Train status:", status)

    previous = {}
    if STATE.exists():
        try:
            previous = json.loads(
                STATE.read_text(encoding="utf-8")
            )
        except (ValueError, OSError):
            pass

    key = now.date().isoformat()

    if status == "ok":
        previous[key] = "ok"

    elif previous.get(key) != status:
        topic = os.environ["NTFY_TOPIC"]

        if cancelled:
            title = "Trein Tiel 07:53 uitgevallen"
            body = (
                "NS meldt dat jouw trein is uitgevallen. "
                "Controleer je reis."
            )
        else:
            title = f"Trein 07:53: {delay} min vertraging"
            body = (
                f"Verwacht vertrek uit Tiel: "
                f"{actual.astimezone(TZ):%H:%M}."
            )

        send_notification(topic, title, body)
        previous[key] = status

    else:
        print("Status ongewijzigd; geen dubbele melding.")

    STATE.write_text(
        json.dumps({key: previous[key]}),
        encoding="utf-8",
    )


def main():
    now = datetime.now(TZ)
    mode = sys.argv[1] if len(sys.argv) > 1 else "monitor"

    print("Local time:", now.isoformat())
    print("Mode:", mode)

    if mode == "test-push":
        send_notification(
            os.environ["NTFY_TOPIC"],
            "Test treinmonitor",
            "GitHub kan meldingen naar je Android sturen!",
        )
        return

    if mode == "test-api":
        departures = get_departures()
        print("Actuele vertrekken uit Tiel:")

        for dep in departures:
            print(
                dep.get("plannedDateTime"),
                "| Richting:", dep.get("direction"),
                "| Route:", dep.get("routeStations"),
            )
        return

    if mode != "monitor":
        raise ValueError("Onbekende modus: " + mode)

    if now.weekday() != 0 or not (
        "07:05" <= now.strftime("%H:%M") <= "07:53"
    ):
        print("Outside monitoring window; skipping.")
        return

    departures = get_departures()
    check_train(departures, now)


if __name__ == "__main__":
    main()
