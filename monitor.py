#!/usr/bin/env python3
"""Monitor the 07:53 Monday NS departure from Tiel and notify via ntfy."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.parse import urlencode

TZ = ZoneInfo('Europe/Amsterdam')
STATE = Path('monitor_state.json')
STATION = 'Tl'  # NS station code: Tiel
DEPARTURE = '07:53'
DESTINATION = 'Utrecht Centraal'


def get_json(url, headers):
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def send_notification(topic, title, body):
    req = Request('https://ntfy.sh/' + topic, data=body.encode('utf-8'),
                  headers={'Title': title, 'Priority': 'high', 'Tags': 'train,warning'}, method='POST')
    with urlopen(req, timeout=20) as response:
        print('ntfy response:', response.status)


def main():
    now = datetime.now(TZ)
    print('Local time:', now.isoformat())
    # GitHub cron is UTC. This guard handles CET/CEST automatically.
    if now.weekday() != 0 or not ('07:05' <= now.strftime('%H:%M') <= '07:53'):
        print('Outside monitoring window; skipping.')
        return
    api_key = os.environ['NS_API_KEY']
    topic = os.environ['NTFY_TOPIC']
    params = urlencode({'station': STATION, 'maxJourneys': 100})
    data = get_json('https://gateway.apiportal.ns.nl/reisinformatie-api/api/v3/departures?' + params,
                    {'Ocp-Apim-Subscription-Key': api_key, 'Accept': 'application/json'})
    departures = data.get('payload', {}).get('departures', [])
    today = now.date()
    matches = []
    for dep in departures:
        planned = dep.get('plannedDateTime')
        if not planned:
            continue
        dt = datetime.fromisoformat(planned.replace('Z', '+00:00')).astimezone(TZ)
        if dt.date() != today or dt.strftime('%H:%M') != DEPARTURE:
            continue
        # Avoid matching a different train departing at the same minute.
        direction = (dep.get('direction') or '').lower()
        route = ' '.join(str(x) for x in dep.get('routeStations', [])) .lower()
        if 'utrecht' not in direction and 'utrecht' not in route:
            continue
        matches.append(dep)
    if not matches:
        # Missing departures can mean a cancellation, but also an API or timetable change.
        print('No matching 07:53 departure. Cannot reliably infer cancellation; no push sent.')
        return
    dep = matches[0]
    planned = datetime.fromisoformat(dep['plannedDateTime'].replace('Z', '+00:00'))
    actual = datetime.fromisoformat((dep.get('actualDateTime') or dep['plannedDateTime']).replace('Z', '+00:00'))
    delay = max(0, round((actual - planned).total_seconds() / 60))
    cancelled = bool(dep.get('cancelled'))
    status = 'cancelled' if cancelled else ('delay:' + str(delay) if delay >= 3 else 'ok')
    print('Train status:', status)
    previous = {}
    if STATE.exists():
        try:
            previous = json.loads(STATE.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    key = today.isoformat()
    if status == 'ok':
        # Clear the state if the delay has been resolved, allowing a new alert later.
        previous[key] = 'ok'
    elif previous.get(key) != status:
        if cancelled:
            title = 'Trein 07:53 Tiel is uitgevallen'
            body = 'De NS meldt dat de trein van 07:53 uit Tiel richting Utrecht Centraal is uitgevallen. Controleer je reis in de NS-app.'
        else:
            title = f'Trein 07:53: {delay} min vertraging'
            body = f'Je sprinter uit Tiel richting Utrecht Centraal vertrekt naar verwachting om {actual.astimezone(TZ):%H:%M} (gepland 07:53).'
        send_notification(topic, title, body)
        previous[key] = status
    else:
        print('Status unchanged; no duplicate notification.')
    STATE.write_text(json.dumps({key: previous[key]}), encoding='utf-8')


if __name__ == '__main__':
    main()
