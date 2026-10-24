import math

import pandas as pd


REQUIRED_COLUMNS = [
    "deliveryTime",
    "selectedPublishTime",
    "forecastGeneration",
    "actualGeneration",
]


def calculate_period_errors(
    processed_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate forecast errors for each delivery period.

    Error formula:
        forecast_generation - actual_generation

    Percentage error is left blank when actual generation is
    missing or zero.
    """
    dataframe = processed_data.copy()

    for column in REQUIRED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe["forecastGeneration"] = pd.to_numeric(
        dataframe["forecastGeneration"],
        errors="coerce",
    )

    dataframe["actualGeneration"] = pd.to_numeric(
        dataframe["actualGeneration"],
        errors="coerce",
    )

    valid_values = (
        dataframe["forecastGeneration"].notna()
        & dataframe["actualGeneration"].notna()
    )

    dataframe["forecastErrorMW"] = None
    dataframe["absoluteErrorMW"] = None
    dataframe["squaredErrorMW"] = None

    dataframe.loc[valid_values, "forecastErrorMW"] = (
        dataframe.loc[valid_values, "forecastGeneration"]
        - dataframe.loc[valid_values, "actualGeneration"]
    )

    dataframe.loc[valid_values, "absoluteErrorMW"] = (
        dataframe.loc[valid_values, "forecastErrorMW"].abs()
    )

    dataframe.loc[valid_values, "squaredErrorMW"] = (
        dataframe.loc[valid_values, "forecastErrorMW"] ** 2
    )

    meaningful_percentage_values = (
        valid_values
        & dataframe["actualGeneration"].ne(0)
    )

    dataframe["percentageError"] = None

    dataframe.loc[
        meaningful_percentage_values,
        "percentageError",
    ] = (
        dataframe.loc[
            meaningful_percentage_values,
            "forecastErrorMW",
        ]
        / dataframe.loc[
            meaningful_percentage_values,
            "actualGeneration",
        ]
        * 100
    )

    return dataframe


def calculate_accuracy_metrics(
    period_errors: pd.DataFrame,
) -> dict:
    """
    Calculate MAE and RMSE using rows with both forecast
    and actual generation values.
    """
    if period_errors.empty:
        return {
            "maeMW": None,
            "rmseMW": None,
            "evaluatedPeriods": 0,
        }

    valid_errors = period_errors[
        period_errors["forecastErrorMW"].notna()
        & period_errors["actualGeneration"].notna()
    ]

    if valid_errors.empty:
        return {
            "maeMW": None,
            "rmseMW": None,
            "evaluatedPeriods": 0,
        }

    absolute_errors = pd.to_numeric(
        valid_errors["absoluteErrorMW"],
        errors="coerce",
    )

    squared_errors = pd.to_numeric(
        valid_errors["squaredErrorMW"],
        errors="coerce",
    )

    mae = absolute_errors.mean()
    rmse = math.sqrt(squared_errors.mean())

    return {
        "maeMW": float(mae),
        "rmseMW": float(rmse),
        "evaluatedPeriods": int(len(valid_errors)),
    }


def calculate_forecast_accuracy(
    processed_data: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Calculate per-period errors and aggregate metrics.
    """
    period_errors = calculate_period_errors(
        processed_data
    )

    metrics = calculate_accuracy_metrics(
        period_errors
    )

    return period_errors, metrics