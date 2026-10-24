import unittest

import pandas as pd

from services.accuracy import (
    calculate_accuracy_metrics,
    calculate_forecast_accuracy,
    calculate_period_errors,
)


class TestForecastAccuracy(unittest.TestCase):

    def test_normal_values(self):
        data = pd.DataFrame(
            [
                {
                    "deliveryTime": "2026-01-01T00:00:00Z",
                    "selectedPublishTime": "2025-12-31T10:00:00Z",
                    "forecastGeneration": 110,
                    "actualGeneration": 100,
                },
                {
                    "deliveryTime": "2026-01-01T00:30:00Z",
                    "selectedPublishTime": "2025-12-31T10:00:00Z",
                    "forecastGeneration": 80,
                    "actualGeneration": 100,
                },
            ]
        )

        period_errors, metrics = calculate_forecast_accuracy(
            data
        )

        self.assertEqual(
            list(period_errors["forecastErrorMW"]),
            [10, -20],
        )

        self.assertEqual(
            list(period_errors["absoluteErrorMW"]),
            [10, 20],
        )

        self.assertAlmostEqual(
            metrics["maeMW"],
            15.0,
        )

        self.assertAlmostEqual(
            metrics["rmseMW"],
            (250 ** 0.5),
        )

        self.assertEqual(
            metrics["evaluatedPeriods"],
            2,
        )

    def test_missing_values_are_excluded_from_metrics(self):
        data = pd.DataFrame(
            [
                {
                    "deliveryTime": "2026-01-01T00:00:00Z",
                    "selectedPublishTime": "2025-12-31T10:00:00Z",
                    "forecastGeneration": 110,
                    "actualGeneration": 100,
                },
                {
                    "deliveryTime": "2026-01-01T00:30:00Z",
                    "selectedPublishTime": None,
                    "forecastGeneration": None,
                    "actualGeneration": 100,
                },
                {
                    "deliveryTime": "2026-01-01T01:00:00Z",
                    "selectedPublishTime": "2025-12-31T10:00:00Z",
                    "forecastGeneration": 90,
                    "actualGeneration": None,
                },
            ]
        )

        period_errors = calculate_period_errors(data)
        metrics = calculate_accuracy_metrics(period_errors)

        self.assertEqual(
            metrics["evaluatedPeriods"],
            1,
        )

        self.assertAlmostEqual(
            metrics["maeMW"],
            10.0,
        )

        # self.assertIsNone(
        #     period_errors.iloc[1]["forecastErrorMW"]
        # )

        self.assertTrue(
    pd.isna(period_errors.iloc[1]["forecastErrorMW"])
)

    def test_zero_actual_generation_has_no_percentage_error(self):
        data = pd.DataFrame(
            [
                {
                    "deliveryTime": "2026-01-01T00:00:00Z",
                    "selectedPublishTime": "2025-12-31T10:00:00Z",
                    "forecastGeneration": 25,
                    "actualGeneration": 0,
                }
            ]
        )

        period_errors = calculate_period_errors(data)

        self.assertEqual(
            period_errors.iloc[0]["forecastErrorMW"],
            25,
        )

        # self.assertIsNone(
        #     period_errors.iloc[0]["percentageError"]
        # )
        self.assertTrue(
    pd.isna(period_errors.iloc[0]["percentageError"])
)

    def test_empty_data(self):
        data = pd.DataFrame()

        period_errors, metrics = calculate_forecast_accuracy(
            data
        )

        self.assertTrue(period_errors.empty)
        self.assertIsNone(metrics["maeMW"])
        self.assertIsNone(metrics["rmseMW"])
        self.assertEqual(metrics["evaluatedPeriods"], 0)


if __name__ == "__main__":
    unittest.main()