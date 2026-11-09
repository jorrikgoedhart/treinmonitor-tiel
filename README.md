# Treinmonitor: Tiel 07:53 → Utrecht Centraal

Deze monitor controleert op maandag tussen **07:05 en 07:53 (Nederlandse tijd)** de NS-vertrekgegevens van Tiel. Bij minimaal **3 minuten vertraging** of expliciete **uitval** verstuurt hij een Android-pushmelding via ntfy. Bij ongewijzigde status wordt geen nieuwe melding verstuurd.

## Stap 1 — NS API-sleutel aanvragen

1. Maak een account aan op https://apiportal.ns.nl/.
2. Abonneer je op de **Reisinformatie API** (controleer de actuele voorwaarden en limieten).
3. Kopieer de subscription key. Deel deze niet publiek.

## Stap 2 — Android instellen

1. Installeer **ntfy** via https://ntfy.sh/ of de Play Store.
2. Kies een **lang, willekeurig topic** (bijvoorbeeld `trein-tiel-7f9d2c...`, niet `treinmonitor`). Topics op de publieke ntfy-server zijn niet privé.
3. Voeg in ntfy een abonnement op precies dat topic toe.
4. Sta meldingen toe en controleer of Android de app niet beperkt door batterijbesparing.
5. Test vanaf een browser of terminal met een POST naar `https://ntfy.sh/JOUW_TOPIC`, bijvoorbeeld met curl: `curl -d 'Testmelding treinmonitor' https://ntfy.sh/JOUW_TOPIC`.

## Stap 3 — GitHub instellen

1. Maak op https://github.com/ een **privérepository** aan, bijvoorbeeld `treinmonitor`.
2. Upload `monitor.py` en `.github/workflows/treinmonitor.yml` met behoud van de mappenstructuur. De map `.github` kan verborgen zijn in sommige bestandsverkenners.
3. Ga naar **Settings → Secrets and variables → Actions → New repository secret**.
4. Maak de secrets `NS_API_KEY` (NS subscription key) en `NTFY_TOPIC` (exact jouw ntfy-topic) aan.
5. Ga naar **Actions**, selecteer **Treinmonitor Tiel 07:53** en schakel workflows in indien nodig.

## Stap 4 — Controleren

1. Open **Actions → Treinmonitor Tiel 07:53 → Run workflow**.
2. Buiten maandagochtend verschijnt in de logs `Outside monitoring window; skipping.`; dat is correct.
3. Voor een echte proef controleer je op maandagochtend de workflowlogs. Als de NS geen trein vindt, zie je een duidelijke melding in de logs maar ontvang je bewust geen push.
4. Controleer ook of de rit werkelijk als **rechtstreekse sprinter richting Utrecht Centraal** in de NS-vertrekgegevens staat. Bij een andere eindbestemming of dienstregeling moet het script worden aangepast.

## Belangrijke beperkingen

- **GitHub Actions is niet gegarandeerd stipt.** Geplande runs kunnen minuten later starten of soms worden overgeslagen. Dit is een best-effort alarm, geen veiligheidskritische dienst.
- De NS API toont alleen beschikbare vertrekgegevens. Als de trein geheel ontbreekt, kan de monitor **niet met zekerheid vaststellen** dat hij is uitgevallen; daarom stuurt hij in dat geval geen valse uitvalmelding.
- De monitor gebruikt een controle op de bestemming/richting `Utrecht`. Als de trein in werkelijkheid een andere eindbestemming op het vertrekbord heeft, wordt hij mogelijk niet gevonden.
- Bij een gewijzigde vertraging (bijv. 5 naar 10 minuten) volgt een nieuwe melding. Bij een onveranderde vertraging niet.
- ntfy.sh is een publieke dienst: gebruik een niet te raden topic en zet er geen persoonsgegevens in. Voor strengere privacy is een eigen ntfy-server mogelijk.
- GitHub kan workflows in weinig actieve repositories automatisch uitschakelen. Controleer af en toe of de workflow nog actief is.
- De gratis limieten en voorwaarden van NS, GitHub en ntfy kunnen wijzigen.

## Aanpassen

- Vertrektijd: `DEPARTURE = '07:53'` in `monitor.py`.
- Meldgrens: `delay >= 3`.
- Controletijden: tijdvenster in `monitor.py`.
- Maandelijkse of extra dagen: pas de cron-regel en de `weekday()`-controle aan.
