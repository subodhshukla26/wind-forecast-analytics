from datetime import date

import pandas as pd

from services.elexon_client import fetch_dataset


def fetch_actual_wind_generation(
    start_date: date,
    end_date: date,
) -> list[dict]:
    params = {
        "settlementDateFrom": start_date.isoformat(),
        "settlementDateTo": end_date.isoformat(),
    }

    records = fetch_dataset("FUELHH", params)

    if not records:
        return []

    dataframe = pd.DataFrame(records)

    if "fuelType" in dataframe.columns:
        dataframe = dataframe[
            dataframe["fuelType"].astype(str).str.upper() == "WIND"
        ]

    required_columns = ["startTime", "generation"]

    for column in required_columns:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[required_columns].copy()
    dataframe["generation"] = pd.to_numeric(
        dataframe["generation"],
        errors="coerce",
    )

    dataframe = dataframe.dropna(
        subset=["startTime", "generation"],
    )

    return dataframe.to_dict(orient="records")