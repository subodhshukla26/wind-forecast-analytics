from datetime import date

from services.accuracy import calculate_forecast_accuracy
from services.processing import build_processed_wind_dataset


processed_data = build_processed_wind_dataset(
    start_date=date(2026, 1, 1),
    end_date=date(2026, 1, 31),
)

period_errors, metrics = calculate_forecast_accuracy(
    processed_data
)

print("Processed rows:", len(processed_data))
print(
    "Rows with forecasts:",
    int(processed_data["forecastGeneration"].notna().sum()),
)
print(
    "Rows with actuals:",
    int(processed_data["actualGeneration"].notna().sum()),
)
print("\nSample calculated errors:")
print(
    period_errors[
        [
            "deliveryTime",
            "selectedPublishTime",
            "forecastGeneration",
            "actualGeneration",
            "forecastErrorMW",
            "percentageError",
        ]
    ]
    .dropna(subset=["forecastGeneration", "actualGeneration"])
    .head()
    .to_string(index=False)
)
print("\nAccuracy metrics:")
print(metrics)
