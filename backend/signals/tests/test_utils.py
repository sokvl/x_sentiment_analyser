from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase

from signals.utils import safe_round, parse_date, date_range, get_data_manager


class SafeRoundTests(TestCase):
    def test_rounds_to_two_decimals_by_default(self):
        self.assertEqual(safe_round(3.14159), 3.14)

    def test_rounds_to_specified_decimals(self):
        self.assertEqual(safe_round(3.14159, 3), 3.142)

    def test_returns_none_for_nan(self):
        self.assertIsNone(safe_round(float('nan')))

    def test_returns_none_for_positive_inf(self):
        self.assertIsNone(safe_round(float('inf')))

    def test_returns_none_for_negative_inf(self):
        self.assertIsNone(safe_round(float('-inf')))

    def test_rounds_zero(self):
        self.assertEqual(safe_round(0.0), 0.0)

    def test_rounds_negative(self):
        self.assertEqual(safe_round(-1.567), -1.57)

    def test_rounds_integer(self):
        self.assertEqual(safe_round(5), 5)


class ParseDateTests(TestCase):
    def test_parses_valid_date(self):
        result = parse_date('2024-01-15')
        self.assertEqual(result, date(2024, 1, 15))

    def test_returns_none_for_invalid_format(self):
        self.assertIsNone(parse_date('15-01-2024'))

    def test_returns_none_for_garbage(self):
        self.assertIsNone(parse_date('not-a-date'))

    def test_returns_none_for_empty_string(self):
        self.assertIsNone(parse_date(''))

    def test_custom_format(self):
        result = parse_date('15/01/2024', format='%d/%m/%Y')
        self.assertEqual(result, date(2024, 1, 15))

    def test_returns_date_not_datetime(self):
        result = parse_date('2024-06-01')
        self.assertIsInstance(result, date)


class DateRangeTests(TestCase):
    def test_single_day_range(self):
        start = date(2024, 1, 1)
        result = list(date_range(start, start))
        self.assertEqual(result, [start])

    def test_multi_day_range(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        result = list(date_range(start, end))
        self.assertEqual(result, [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3),
        ])

    def test_empty_range_when_end_before_start(self):
        result = list(date_range(date(2024, 1, 5), date(2024, 1, 1)))
        self.assertEqual(result, [])


class GetDataManagerTests(TestCase):
    @patch('signals.utils.apps')
    def test_returns_data_manager_when_available(self, mock_apps):
        mock_dm = MagicMock()
        mock_apps.get_app_config.return_value.DATA_MANAGER = mock_dm
        dm, error = get_data_manager()
        self.assertEqual(dm, mock_dm)
        self.assertIsNone(error)

    @patch('signals.utils.apps')
    def test_returns_error_when_not_available(self, mock_apps):
        mock_apps.get_app_config.return_value = MagicMock(spec=[])
        dm, error = get_data_manager()
        self.assertIsNone(dm)
        self.assertIsNotNone(error)
