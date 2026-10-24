from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from services.actuals import fetch_actual_wind_generation
from services.forecasts import fetch_wind_forecasts


LONDON_TIMEZONE = ZoneInfo("Europe/London")
UTC_TIMEZONE = ZoneInfo("UTC")

DEFAULT_DECISION_TIME = time(hour=10, minute=0)


class ProcessingError(Exception):
    """Raised when Phase 3 processing fails."""


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
            "actualGeneration",
        ]
    )


def _normalise_actuals(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=["deliveryTime", "actualGeneration"]
        )

    dataframe = pd.DataFrame(records)

    dataframe["deliveryTime"] = pd.to_datetime(
        dataframe["startTime"],
        errors="coerce",
        utc=True,
    )

    dataframe["actualGeneration"] = pd.to_numeric(
        dataframe["generation"],
        errors="coerce",
    )

    dataframe = dataframe[
        [
            "deliveryTime",
            "actualGeneration",
        ]
    ]

    dataframe = dataframe.dropna(
        subset=["deliveryTime"]
    )

    dataframe = dataframe.sort_values(
        by=["deliveryTime"]
    )

    # Keep one actual value per delivery period.
    dataframe = dataframe.drop_duplicates(
        subset=["deliveryTime"],
        keep="last",
    )

    return dataframe


def _normalise_forecasts(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "deliveryTime",
                "publishTime",
                "forecastGeneration",
            ]
        )

    dataframe = pd.DataFrame(records)

    dataframe["deliveryTime"] = pd.to_datetime(
        dataframe["startTime"],
        errors="coerce",
        utc=True,
    )

    dataframe["publishTime"] = pd.to_datetime(
        dataframe["publishTime"],
        errors="coerce",
        utc=True,
    )

    dataframe["forecastGeneration"] = pd.to_numeric(
        dataframe["generation"],
        errors="coerce",
    )

    dataframe = dataframe[
        [
            "deliveryTime",
            "publishTime",
            "forecastGeneration",
        ]
    ]

    dataframe = dataframe.dropna(
        subset=[
            "deliveryTime",
            "publishTime",
        ]
    )

    dataframe = dataframe.sort_values(
        by=[
            "deliveryTime",
            "publishTime",
        ]
    )

    # Remove exact duplicate delivery/publication records.
    dataframe = dataframe.drop_duplicates(
        subset=[
            "deliveryTime",
            "publishTime",
        ],
        keep="last",
    )

    return dataframe


def _decision_cutoff_utc(
    delivery_time: pd.Timestamp,
    decision_time: time,
) -> pd.Timestamp:
    delivery_time_london = delivery_time.tz_convert(
        LONDON_TIMEZONE
    )

    decision_date = (
        delivery_time_london.date() - timedelta(days=1)
    )

    decision_datetime_london = datetime.combine(
        decision_date,
        decision_time,
    ).replace(tzinfo=LONDON_TIMEZONE)

    decision_datetime_utc = decision_datetime_london.astimezone(
        UTC_TIMEZONE
    )

    return pd.Timestamp(decision_datetime_utc)


def _select_latest_eligible_forecast(
    forecasts: pd.DataFrame,
    decision_time: time,
) -> pd.DataFrame:
    if forecasts.empty:
        return pd.DataFrame(
            columns=[
                "deliveryTime",
                "selectedPublishTime",
                "forecastGeneration",
            ]
        )

    selected_rows = []

    for delivery_time, delivery_group in forecasts.groupby(
        "deliveryTime",
        sort=True,
    ):
        cutoff = _decision_cutoff_utc(
            delivery_time=delivery_time,
            decision_time=decision_time,
        )

        eligible_forecasts = delivery_group[
            delivery_group["publishTime"] <= cutoff
        ]

        if eligible_forecasts.empty:
            selected_rows.append(
                {
                    "deliveryTime": delivery_time,
                    "selectedPublishTime": pd.NaT,
                    "forecastGeneration": None,
                }
            )
            continue

        latest_forecast = eligible_forecasts.sort_values(
            by=["publishTime"]
        ).iloc[-1]

        selected_rows.append(
            {
                "deliveryTime": delivery_time,
                "selectedPublishTime": latest_forecast[
                    "publishTime"
                ],
                "forecastGeneration": latest_forecast[
                    "forecastGeneration"
                ],
            }
        )

    return pd.DataFrame(selected_rows)


def build_processed_wind_dataset(
    start_date: date,
    end_date: date,
    decision_time: time = DEFAULT_DECISION_TIME,
) -> pd.DataFrame:
    if start_date > end_date:
        raise ProcessingError(
            "start_date must be before or equal to end_date"
        )

    try:
        actual_records = fetch_actual_wind_generation(
            start_date=start_date,
            end_date=end_date,
        )

        forecast_records = fetch_wind_forecasts(
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        raise ProcessingError(
            f"Unable to retrieve Phase 2 data: {exc}"
        ) from exc

    actuals = _normalise_actuals(actual_records)
    forecasts = _normalise_forecasts(forecast_records)

    selected_forecasts = _select_latest_eligible_forecast(
        forecasts=forecasts,
        decision_time=decision_time,
    )

    if selected_forecasts.empty and actuals.empty:
        return _empty_result()

    processed = pd.merge(
        selected_forecasts,
        actuals,
        on="deliveryTime",
        how="outer",
    )

    processed = processed.sort_values(
        by=["deliveryTime"]
    )

    processed["deliveryTime"] = processed[
        "deliveryTime"
    ].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    processed["selectedPublishTime"] = pd.to_datetime(
        processed["selectedPublishTime"],
        errors="coerce",
        utc=True,
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    processed = processed[
        [
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
            "actualGeneration",
        ]
    ]

    return processed