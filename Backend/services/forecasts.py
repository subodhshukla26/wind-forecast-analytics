from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from services.elexon_client import fetch_dataset


def _utc_start(date_value: date) -> str:
    value = datetime.combine(
        date_value,
        time.min,
        tzinfo=timezone.utc,
    )
    return value.isoformat().replace("+00:00", "Z")


def _utc_end(date_value: date) -> str:
    value = datetime.combine(
        date_value,
        time.max,
        tzinfo=timezone.utc,
    )
    return value.isoformat().replace("+00:00", "Z")


def fetch_wind_forecasts(
    start_date: date,
    end_date: date,
) -> list[dict]:
    # WINDFOR stream data is filtered by publication time. Include a
    # lookback window so forecasts published before the first delivery
    # date can still be selected for day-ahead decisions.
    publication_start = start_date - timedelta(days=14)
    publication_end = end_date + timedelta(days=1)

    params = {
        "publishDateTimeFrom": _utc_start(publication_start),
        "publishDateTimeTo": _utc_end(publication_end),
    }

    records = fetch_dataset("WINDFOR", params)

    if not records:
        return []

    dataframe = pd.DataFrame(records)

    required_columns = [
        "startTime",
        "publishTime",
        "generation",
    ]

    for column in required_columns:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[required_columns].copy()

    dataframe["startTime"] = pd.to_datetime(
        dataframe["startTime"],
        errors="coerce",
        utc=True,
    )

    dataframe["publishTime"] = pd.to_datetime(
        dataframe["publishTime"],
        errors="coerce",
        utc=True,
    )

    dataframe["generation"] = pd.to_numeric(
        dataframe["generation"],
        errors="coerce",
    )

    dataframe = dataframe.dropna(
        subset=[
            "startTime",
            "publishTime",
            "generation",
        ],
    )

    start_timestamp = pd.Timestamp(
        start_date,
        tz="UTC",
    )

    end_timestamp = pd.Timestamp(
        end_date,
        tz="UTC",
    ) + pd.Timedelta(days=1)

    dataframe = dataframe[
        (dataframe["startTime"] >= start_timestamp)
        & (dataframe["startTime"] < end_timestamp)
    ]

    dataframe["startTime"] = dataframe["startTime"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    dataframe["publishTime"] = dataframe["publishTime"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return dataframe.to_dict(orient="records")
