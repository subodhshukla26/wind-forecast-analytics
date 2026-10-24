from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from services.actuals import fetch_actual_wind_generation
from services.elexon_client import ElexonAPIError
from services.forecasts import fetch_wind_forecasts
from datetime import time, date
import pandas as pd

from services.accuracy import calculate_forecast_accuracy
from services.processing import (
    ProcessingError,
    build_processed_wind_dataset,
)
from services.processing import (
    ProcessingError,
    build_processed_wind_dataset,
)

app = FastAPI(
    title="UK Wind Forecast Analytics API",
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Backend is running",
    }


@app.get("/api/actuals")
def get_actual_wind_generation(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
) -> dict:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    try:
        data = fetch_actual_wind_generation(
            start_date=start_date,
            end_date=end_date,
        )
    except ElexonAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startDate": start_date,
        "endDate": end_date,
        "count": len(data),
        "data": data,
    }


@app.get("/api/forecasts")
def get_wind_forecasts(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
) -> dict:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    try:
        data = fetch_wind_forecasts(
            start_date=start_date,
            end_date=end_date,
        )
    except ElexonAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "dataset": "WINDFOR",
        "startDate": start_date,
        "endDate": end_date,
        "count": len(data),
        "data": data,
    }

@app.get("/api/forecasts/latest")
def get_latest_eligible_forecasts(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
    decision_hour: int = Query(
        default=10,
        ge=0,
        le=23,
        description="Purchasing decision hour in Europe/London",
    ),
    decision_minute: int = Query(
        default=0,
        ge=0,
        le=59,
        description="Purchasing decision minute",
    ),
) -> dict:
    processed_data = load_processed_data(
        start_date=start_date,
        end_date=end_date,
        decision_hour=decision_hour,
        decision_minute=decision_minute,
    )

    forecasts = processed_data[
        processed_data["forecastGeneration"].notna()
    ][
        [
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
        ]
    ]

    if forecasts.empty:
        raise HTTPException(
            status_code=404,
            detail="No eligible forecasts found for the requested period",
        )

    return {
        "dataset": "WINDFOR",
        "startDate": start_date,
        "endDate": end_date,
        "decisionTime": (
            f"{decision_hour:02d}:"
            f"{decision_minute:02d} Europe/London"
        ),
        "count": len(forecasts),
        "data": dataframe_to_records(forecasts),
    }

@app.get("processed")
def get_processed_wind_dataset(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
    decision_hour: int = Query(
        default=10,
        ge=0,
        le=23,
        description=(
            "Day-ahead purchasing decision hour "
            "in Europe/London"
        ),
    ),
    decision_minute: int = Query(
        default=0,
        ge=0,
        le=59,
        description=(
            "Day-ahead purchasing decision minute "
            "in Europe/London"
        ),
    ),
) -> dict:
    try:
        processed_data = build_processed_wind_dataset(
            start_date=start_date,
            end_date=end_date,
            decision_time=time(
                hour=decision_hour,
                minute=decision_minute,
            ),
        )
    except ProcessingError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    processed_data = processed_data.where(
        processed_data.notna(),
        None,
    )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "decisionTime": (
            f"{decision_hour:02d}:"
            f"{decision_minute:02d} Europe/London"
        ),
        "count": len(processed_data),
        "data": processed_data.to_dict(
            orient="records"
        ),
    }

@app.get("/api/comparison")
def get_forecast_actual_comparison(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
    decision_hour: int = Query(
        default=10,
        ge=0,
        le=23,
    ),
    decision_minute: int = Query(
        default=0,
        ge=0,
        le=59,
    ),
) -> dict:
    processed_data = load_processed_data(
        start_date=start_date,
        end_date=end_date,
        decision_hour=decision_hour,
        decision_minute=decision_minute,
    )

    comparison = processed_data[
        processed_data["forecastGeneration"].notna()
        & processed_data["actualGeneration"].notna()
    ][
        [
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
            "actualGeneration",
        ]
    ]

    if comparison.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                "No forecast and actual pairs found "
                "for the requested period"
            ),
        )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "count": len(comparison),
        "data": dataframe_to_records(comparison),
    }

@app.get("/api/accuracy/summary")
def get_accuracy_summary(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
    decision_hour: int = Query(
        default=10,
        ge=0,
        le=23,
    ),
    decision_minute: int = Query(
        default=0,
        ge=0,
        le=59,
    ),
) -> dict:
    processed_data = load_processed_data(
        start_date=start_date,
        end_date=end_date,
        decision_hour=decision_hour,
        decision_minute=decision_minute,
    )

    _, metrics = calculate_forecast_accuracy(
        processed_data
    )

    if metrics["evaluatedPeriods"] == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Accuracy metrics cannot be calculated because "
                "no paired forecast and actual values were found"
            ),
        )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "metrics": metrics,
    }

@app.get("/api/errors")
def get_detailed_forecast_errors(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date",
    ),
    decision_hour: int = Query(
        default=10,
        ge=0,
        le=23,
    ),
    decision_minute: int = Query(
        default=0,
        ge=0,
        le=59,
    ),
) -> dict:
    processed_data = load_processed_data(
        start_date=start_date,
        end_date=end_date,
        decision_hour=decision_hour,
        decision_minute=decision_minute,
    )

    period_errors, metrics = calculate_forecast_accuracy(
        processed_data
    )

    detailed_errors = period_errors[
        period_errors["forecastGeneration"].notna()
        & period_errors["actualGeneration"].notna()
    ][
        [
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
            "actualGeneration",
            "forecastErrorMW",
            "absoluteErrorMW",
            "percentageError",
        ]
    ]

    if detailed_errors.empty:
        raise HTTPException(
            status_code=404,
            detail="No detailed forecast errors found",
        )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "evaluatedPeriods": metrics["evaluatedPeriods"],
        "count": len(detailed_errors),
        "data": dataframe_to_records(detailed_errors),
    }

JANUARY_2026_START = date(2026, 1, 1)
JANUARY_2026_END = date(2026, 1, 31)


def validate_january_date_range(
    start_date: date,
    end_date: date,
) -> None:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date",
        )

    if start_date < JANUARY_2026_START:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be before 2026-01-01",
        )

    if end_date > JANUARY_2026_END:
        raise HTTPException(
            status_code=400,
            detail="end_date cannot be after 2026-01-31",
        )


def load_processed_data(
    start_date: date,
    end_date: date,
    decision_hour: int,
    decision_minute: int,
) -> pd.DataFrame:
    validate_january_date_range(
        start_date=start_date,
        end_date=end_date,
    )

    try:
        return build_processed_wind_dataset(
            start_date=start_date,
            end_date=end_date,
            decision_time=time(
                hour=decision_hour,
                minute=decision_minute,
            ),
        )
    except ProcessingError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict]:
    """
    Convert Pandas missing values to JSON null values.
    """
    clean_dataframe = dataframe.astype(object).where(
        pd.notna(dataframe),
        None,
    )

    return clean_dataframe.to_dict(
        orient="records"
    )