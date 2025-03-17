from typing import TypedDict, Optional, List, Dict, Any
import requests
from datetime import datetime, timedelta, timezone
import pytz

class PriceEntry(TypedDict):
    startDate: datetime
    endDate: datetime
    price: float

class RawPriceEntry(TypedDict):
    startDate: str
    endDate: str
    price: float

LATEST_PRICES_ENDPOINT = "https://api.porssisahko.net/v1/latest-prices.json"

# Globaali välimuisti (cache)
_cached_prices: Optional[List[PriceEntry]] = None
_next_refresh_time: Optional[datetime] = None


def parse_iso_zulu(dt_string: str) -> datetime:
    """
    Parsii esim. "2022-11-14T22:00:00.000Z" Python-datetimeksi (UTC).
    Toimii Python 3.6 -ympäristössä, jossa ei ole datetime.fromisoformat().
    """
    # %Y = 4-numeroa vuodelle
    # %m = 2-numeroa kuukaudelle
    # %d = 2-numeroa päivälle
    # T = merkkijono "T"
    # %H = 2-numeroa tunnille (00..23)
    # %M = 2-numeroa minuuteille (00..59)
    # %S = 2-numeroa sekunneille (00..59)
    # .%f = sekuntien murto-osa (mikrosekuntia), esim. .000
    # Z on merkkijono lopussa
    dt = datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.replace(tzinfo=timezone.utc)  # asetetaan UTC-aikavyöhyke


def fetch_latest_price_data() -> Dict[str, Any]:
    """
    Hakee rajapinnasta viimeisimmät 48 tunnin hinnat (snt/kWh).
    Palauttaa vastauksen JSON-muodossa.
    """
    response = requests.get(LATEST_PRICES_ENDPOINT)
    response.raise_for_status()  # Heittää virheen, jos pyyntö epäonnistuu
    return response.json()

def convert_price_data(prices: List[RawPriceEntry]) -> List[PriceEntry]:
    # Create and return a new list without modifying input inline
    converted_prices: List[PriceEntry] = []
    for price_info in prices:
        converted_prices.append({
            "startDate": parse_iso_zulu(price_info["startDate"]),
            "endDate": parse_iso_zulu(price_info["endDate"]),
            "price": price_info["price"]
        })
    return converted_prices

def get_price_for_datetime(dt: datetime, prices: List[PriceEntry]) -> float:
    """
    Palauttaa hinnan annetulle ajankohdalle dt (datetime-oliona, UTC).
    prices on lista, jossa jokaisella alkioilla on:
       {
         "price": <float, snt/kWh>,
         "startDate": <ISO8601 UTC-string esim. '2022-11-14T22:00:00.000Z'>,
         "endDate": <ISO8601 UTC-string esim. '2022-11-14T23:00:00.000Z'>
       }
    """
    for price_info in prices:
        if price_info['startDate'] <= dt < price_info['endDate']:
            return price_info['price']

    raise ValueError("Hintaa ei löytynyt annetulle ajanhetkelle.")


def get_next_refresh_time() -> datetime:
    tz = pytz.timezone("Europe/Helsinki")
    now_local = datetime.now(tz)
    refresh_time = now_local.replace(hour=1, minute=0, second=5, microsecond=0)

    if now_local >= refresh_time:
        refresh_time += timedelta(days=1)

    return refresh_time


def get_current_spot_price() -> float:
    """
    Palauttaa (nykyhetkeä vastaavan) spot-hinnan snt/kWh.
    Päivittää tarvittaessa cachet, jos kello on ylittänyt 16:00 (Helsingin aikaa).
    """
    global _cached_prices, _next_refresh_time

    if _cached_prices is None or _next_refresh_time is None:
        # Ei ole vielä dataa, haetaan heti ja asetetaan seuraava päivitysaika
        data = fetch_latest_price_data()
        _cached_prices = convert_price_data(data["prices"])
        _next_refresh_time = get_next_refresh_time()
    else:
        # Tarkista, onko nykyhetki ylittänyt seuraavan päivitysajankohdan
        tz = pytz.timezone("Europe/Helsinki")
        now_local = datetime.now(tz)
        if now_local >= _next_refresh_time:
            # Päivitetään data
            data = fetch_latest_price_data()
            _cached_prices = convert_price_data(data["prices"])
            _next_refresh_time = get_next_refresh_time()

    # Etsitään hinta nykyhetkelle UTC-ajassa
    now_utc = datetime.now(timezone.utc)
    return get_price_for_datetime(now_utc, _cached_prices)



def get_threshold_for_hours(hours: int = 3) -> float:
    """
    Etsii listasta (prices) hinnan raja-arvon ainoastaan kuluvalta vuorokaudelta, jolla voidaan ajaa
    laitetta 'hours' tuntia vuorokaudessa halvimmilla tunneilla.
    Palauttaa sen suurimman hinnan (snt/kWh), joka sisältyy halvimpiin 'hours' tunnin hintoihin.
    """
    get_current_spot_price()  # päivitetään cache
    prices: List[PriceEntry] = _cached_prices  # type: ignore
    # Suodatetaan vain tämän päivän hinnat
    tz = pytz.timezone("Europe/Helsinki")
    today = datetime.now(tz).date()
    todays_prices: List[PriceEntry] = []
    for price_info in prices:
        start_local = price_info['startDate'].astimezone(tz)
        if start_local.date() == today:
            todays_prices.append(price_info)
    if not todays_prices:
        raise ValueError("Ei hintadataa tälle päivälle.")
    if hours <= 0:
        raise ValueError("hours on oltava positiivinen kokonaisluku.")

    sorted_prices = sorted(todays_prices, key=lambda p: p['price'])
    if hours > len(sorted_prices):
        raise ValueError(f"Dataa on vain {len(sorted_prices)} tuntia tälle päivälle, pyydettiin {hours} tuntia.")
    cheapest_hours = sorted_prices[:hours]
    threshold_price = max(h['price'] for h in cheapest_hours)
    return threshold_price

if __name__ == "__main__":
    # Esimerkki, miten käyttö voisi mennä
    try:
        # Hae/tai päivitä globaali cache
        current_price = get_current_spot_price()
        print(f"Sähkön spothinta nyt: {current_price} snt/kWh (sis. alv)")

        # Haetaan suoraan globaali välimuisti, jotta ei turhaan ladata dataa uudelleen
        if _cached_prices:
            # Etsi esim. 3 tunnin halvimpiin tunteihin sopiva raja-arvo
            threshold = get_threshold_for_hours(hours=3)
            print(f"3 halvimman tunnin raja-arvohinta: {threshold} snt/kWh")
        else:
            print("Ei hintadataa cache:ssa.")

    except Exception as e:
        print(f"Virhe hinnan haussa: {e}")