import unittest

import pandas as pd

from src.data import compute_metrics


def make_series(values, end="2026-09-25"):
    idx = pd.date_range(end=end, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


class ComputeMetricsTest(unittest.TestCase):
    def test_changes_and_52w_range(self):
        # 400 días: sube de 100 a 200 y luego cae a 150 en los últimos días
        values = list(range(100, 200)) + [200] * 290 + [190, 180, 170, 160, 155, 152, 151, 150, 150, 150]
        m = compute_metrics(make_series(values))
        self.assertEqual(m.last, 150)
        self.assertEqual(m.high_52w, 200)
        self.assertAlmostEqual(m.from_high_pct, -25.0)
        # hace 7 días el cierre era 170 -> 150/170 - 1
        self.assertAlmostEqual(m.change_1w, (150 / 170 - 1) * 100)

    def test_weekly_change_uses_value_seven_days_before(self):
        s = make_series([100.0] * 30 + [110.0] * 7 + [121.0])
        m = compute_metrics(s)
        # hace 7 días el cierre era 110 -> 121/110 - 1 = 10 %
        self.assertAlmostEqual(m.change_1w, 10.0)

    def test_short_history_returns_none_changes(self):
        m = compute_metrics(make_series([10.0, 11.0, 12.0]))
        self.assertIsNone(m.change_1w)
        self.assertIsNone(m.change_1m)

    def test_nans_are_ignored(self):
        s = make_series([100.0, float("nan"), 105.0])
        self.assertEqual(compute_metrics(s).last, 105.0)

    def test_empty_series_raises(self):
        with self.assertRaises(ValueError):
            compute_metrics(pd.Series([], dtype=float))


if __name__ == "__main__":
    unittest.main()
