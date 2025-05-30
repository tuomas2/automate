try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict
from typing import Optional, List, Dict, Any
import requests
from datetime import datetime, timedelta, timezone, time
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

# Global cache
_cached_prices: Optional[List[PriceEntry]] = None
_next_refresh_time: Optional[datetime] = None

tz = pytz.timezone("Europe/Helsinki")

def parse_iso_zulu(dt_string: str) -> datetime:
    """
    Parses e.g. "2022-11-14T22:00:00.000Z" to a Python datetime object (UTC).
    Works in Python 3.6 environments where datetime.fromisoformat() is not available.
    """
    # %Y = 4-digit year
    # %m = 2-digit month
    # %d = 2-digit day
    # T = literal "T"
    # %H = 2-digit hour (00..23)
    # %M = 2-digit minute (00..59)
    # %S = 2-digit second (00..59)
    # .%f = fractional second (microseconds), e.g. .000
    # Z is a literal at the end
    dt = datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def fetch_latest_price_data() -> Dict[str, Any]:
    """
    Fetches the latest 48 hours prices (cents/kWh) from the API.
    Returns the response in JSON format.
    """
    response = requests.get(LATEST_PRICES_ENDPOINT)
    response.raise_for_status()  # Raises an error if the request fails
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
    Returns the price for the given datetime dt (UTC).
    """
    for price_info in prices:
        if price_info['startDate'] <= dt < price_info['endDate']:
            return price_info['price']

    raise ValueError("No price found for the given datetime.")


def get_next_refresh_time() -> datetime:
    now_local = datetime.now(tz)
    refresh_time = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    if now_local >= refresh_time:
        refresh_time += timedelta(days=1)

    return refresh_time


def get_current_spot_price(exception_hours: List[int] = None) -> float:
    """
    Returns the current spot price (cents/kWh).
    Refreshes the cache if the local time is past the refresh time.
    
    Parameters:
    - exception_hours: List of hour values (0-23) to exclude. Returns float('inf') for these hours.
    """
    global _cached_prices, _next_refresh_time

    if _cached_prices is None or _next_refresh_time is None:
        # No data yet, fetch immediately and set the next refresh time
        data = fetch_latest_price_data()
        _cached_prices = convert_price_data(data["prices"])
        _next_refresh_time = get_next_refresh_time()
    else:
        # Check if the current time has passed the next refresh time
        now_local = datetime.now(tz)
        if now_local >= _next_refresh_time:
            # Update data
            data = fetch_latest_price_data()
            _cached_prices = convert_price_data(data["prices"])
            _next_refresh_time = get_next_refresh_time()

    # Find the price for the current time in Helsinki
    now_local = datetime.now(tz)
    
    # Return infinity if current hour is in exception_hours
    if exception_hours and now_local.hour in exception_hours:
        return 1.0 # High price during exception hours to make device to not run
    
    return get_price_for_datetime(now_local, _cached_prices)


def get_threshold_for_hours(hours: int = 3, exception_hours: List[int] = None) -> float:
    """
    Determines the threshold price for running the device during the cheapest 'hours' today.
    Returns the highest price among the cheapest 'hours' hours (cents/kWh).
    
    Parameters:
    - hours: Number of cheapest hours to consider
    - exception_hours: List of hour values (0-23) to exclude from consideration
    """
    get_current_spot_price()  # update cache
    prices: List[PriceEntry] = _cached_prices  # type: ignore
    today = datetime.now(tz).date()
    
    # Compute today's boundaries in local time
    start_local = tz.localize(datetime.combine(today, time.min))
    end_local = start_local + timedelta(days=1)
    
    # Filter prices within today's local boundaries
    todays_prices: List[PriceEntry] = []
    for price_info in prices:
        if start_local <= price_info['startDate'] < end_local:
            # Skip exception hours if specified
            if exception_hours and price_info['startDate'].hour in exception_hours:
                continue
            todays_prices.append(price_info)
    
    if not todays_prices:
        raise ValueError("No price data for today (or all hours were excluded).")
    if hours <= 0:
        raise ValueError("hours must be a positive integer.")
    
    sorted_prices = sorted(todays_prices, key=lambda p: p['price'])
    if hours > len(sorted_prices):
        raise ValueError(f"Data contains only {len(sorted_prices)} hours for today (after excluding exception hours), but {hours} hours were requested.")
    cheapest_hours = sorted_prices[:hours]
    threshold_price = max(h['price'] for h in cheapest_hours)
    return threshold_price

if __name__ == "__main__":
    # Example usage
    try:
        # Fetch/update global cache
        current_price = get_current_spot_price()
        print(f"Current spot price: {current_price} cents/kWh (incl. VAT)")

        # Use global cache to avoid unnecessary data reload
        if _cached_prices:
            # Determine threshold for the cheapest 3 hours
            threshold = get_threshold_for_hours(hours=3)
            print(f"Threshold price for the cheapest 3 hours: {threshold} cents/kWh")
        else:
            print("No price data in cache.")

    except Exception as e:
        print(f"Error fetching price: {e}")
