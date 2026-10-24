import requests


ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
REQUEST_TIMEOUT_SECONDS = 30


class ElexonAPIError(Exception):
    """Raised when an Elexon API request fails."""


def fetch_dataset(dataset: str, params: dict) -> list[dict]:
    url = f"{ELEXON_BASE_URL}/datasets/{dataset}/stream"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise ElexonAPIError("Elexon API request timed out") from exc
    except requests.RequestException as exc:
        raise ElexonAPIError(
            f"Elexon API request failed: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ElexonAPIError("Elexon API returned invalid JSON") from exc

    if isinstance(payload, dict):
        records = payload.get("data", [])
    elif isinstance(payload, list):
        records = payload
    else:
        raise ElexonAPIError("Unexpected Elexon API response format")

    if not isinstance(records, list):
        raise ElexonAPIError("Unexpected Elexon API data format")

    return records