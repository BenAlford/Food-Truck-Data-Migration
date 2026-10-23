# pylint: skip-file
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

# extract opens a DB connection on import, so stub it out.
sys.modules.setdefault("extract", SimpleNamespace(
    extract_all_transaction_data=lambda: None))

from transform import clean_transaction_data, split_by_date, transform  # noqa: E402


TRUCK_DF = pd.DataFrame({"truck_id": [1, 2, 3, 4, 5, 6]})
PAYMENT_DF = pd.DataFrame({"payment_method_id": [1, 2]})


def make_df(**overrides):
    row = {
        "total": 5.0,
        "payment_method_id": 1,
        "truck_id": 1,
        "at": pd.Timestamp("2024-01-01 12:00:00"),
    }
    row.update(overrides)
    return pd.DataFrame([row])


def clean(df):
    return clean_transaction_data(df, TRUCK_DF, PAYMENT_DF)


class TestCleanTransactionData:
    def test_valid_row_is_kept(self):
        assert len(clean(make_df())) == 1

    def test_does_not_mutate_input(self):
        df = make_df(total="abc")
        clean(df)
        assert df["total"].iloc[0] == "abc"

    def test_total_is_converted_from_pence_to_pounds(self):
        result = clean(make_df(total="750"))
        assert result["total"].iloc[0] == pytest.approx(7.5)

    def test_non_numeric_total_is_dropped(self):
        assert clean(make_df(total="abc")).empty

    def test_missing_total_is_dropped(self):
        assert clean(make_df(total=None)).empty

    def test_negative_total_is_dropped(self):
        assert clean(make_df(total=-1)).empty

    def test_zero_total_is_kept(self):
        assert len(clean(make_df(total=0))) == 1

    @pytest.mark.parametrize("method_id", [1, 2])
    def test_valid_payment_methods_are_kept(self, method_id):
        assert len(clean(make_df(payment_method_id=method_id))) == 1

    @pytest.mark.parametrize("method_id", [0, 3, -1])
    def test_invalid_payment_methods_are_dropped(self, method_id):
        assert clean(make_df(payment_method_id=method_id)).empty

    @pytest.mark.parametrize("truck_id", [1, 2, 3, 4, 5, 6])
    def test_valid_trucks_are_kept(self, truck_id):
        assert len(clean(make_df(truck_id=truck_id))) == 1

    @pytest.mark.parametrize("truck_id", [0, 7, -1])
    def test_invalid_trucks_are_dropped(self, truck_id):
        assert clean(make_df(truck_id=truck_id)).empty

    def test_future_timestamp_is_dropped(self):
        future = pd.Timestamp.now() + pd.Timedelta(hours=1)
        assert clean(make_df(at=future)).empty

    def test_timestamp_within_grace_period_is_kept(self):
        soon = pd.Timestamp.now() + pd.Timedelta(minutes=2)
        assert len(clean(make_df(at=soon))) == 1

    def test_only_invalid_rows_are_removed(self):
        df = pd.concat([make_df(), make_df(total=-5), make_df(truck_id=99)],
                       ignore_index=True)
        result = clean(df)
        assert len(result) == 1
        assert result["truck_id"].iloc[0] == 1


class TestSplitByDate:
    def test_groups_rows_by_day(self):
        df = pd.concat([
            make_df(at=pd.Timestamp("2024-01-01 09:00")),
            make_df(at=pd.Timestamp("2024-01-01 18:00")),
            make_df(at=pd.Timestamp("2024-01-02 10:00")),
        ], ignore_index=True)

        result = dict(split_by_date(df))

        assert set(result) == {"2024-01-01", "2024-01-02"}
        assert len(result["2024-01-01"]) == 2
        assert len(result["2024-01-02"]) == 1

    def test_keys_are_formatted_yyyy_mm_dd(self):
        result = dict(split_by_date(
            make_df(at=pd.Timestamp("2024-03-05 23:59"))))
        assert list(result) == ["2024-03-05"]

    def test_groups_are_copies(self):
        df = make_df()
        group = dict(split_by_date(df))["2024-01-01"]
        group["total"] = 999
        assert df["total"].iloc[0] == 5.0

    def test_empty_dataframe_yields_nothing(self):
        df = pd.DataFrame({"at": pd.Series([], dtype="datetime64[ns]")})
        assert dict(split_by_date(df)) == {}


class TestTransform:
    def test_returns_cleaned_dataframe(self):
        df = pd.concat([
            make_df(at=pd.Timestamp("2024-01-01 09:00")),
            make_df(at=pd.Timestamp("2024-01-02 09:00")),
            make_df(at=pd.Timestamp("2024-01-02 10:00"), total=-1),
        ], ignore_index=True)

        result = transform(df, TRUCK_DF, PAYMENT_DF)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_does_not_mutate_input(self):
        df = pd.concat([make_df(), make_df(total=-1)], ignore_index=True)
        transform(df, TRUCK_DF, PAYMENT_DF)
        assert len(df) == 2
