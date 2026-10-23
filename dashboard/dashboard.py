import altair as alt
import pandas as pd
from os import environ
from textwrap import wrap
from typing import Optional
import streamlit as st
from dotenv import load_dotenv
from read_athena import fetch_truck_data, fetch_payment_method_data, fetch_transaction_data

load_dotenv()

st.set_page_config(page_title="Food Truck Performance", layout="wide")

# Newlines in wrapped labels are split into separate lines by labelExpr.
WRAPPED_AXIS = alt.Axis(labelAngle=0, labelLimit=0, labelOverlap=False,
                        labelExpr="split(datum.label, '\\n')")


def wrap_label(name) -> str:
    return "\n".join(wrap(str(name), 13))


def static_chart(data: pd.DataFrame, mark: str, x_type: str,
                 x_title: str, y_title: str, legend_title: Optional[str] = None,
                 color_scale: Optional[alt.Scale] = None) -> alt.Chart:
    """Altair chart without .interactive(), so scrolling doesn't zoom it."""
    index = data.index.name
    long = data.reset_index().melt(
        id_vars=index, var_name="series", value_name="value")
    if x_type == "N":
        long["label"] = long[index].map(wrap_label)
        x = alt.X("label:N", title=x_title, sort=None, axis=WRAPPED_AXIS)
    else:
        x = alt.X(f"{index}:{x_type}", title=x_title)
    chart = alt.Chart(long).encode(x=x, y=alt.Y("value:Q", title=y_title))
    chart = chart.mark_line() if mark == "line" else chart.mark_bar()
    scale = color_scale or alt.Undefined
    if data.shape[1] > 1:
        chart = chart.encode(color=alt.Color(
            "series:N", title=legend_title, scale=scale))
    elif color_scale is not None:
        chart = chart.encode(color=alt.Color(
            f"{index}:N", scale=color_scale, legend=None))
    return chart


@st.cache_data(ttl=600)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    database = environ.get("GLUE_DATABASE")
    truck = fetch_truck_data(database)
    payment_method = fetch_payment_method_data(database)
    transaction = fetch_transaction_data(database)
    df = transaction.merge(truck, on="truck_id").merge(
        payment_method, on="payment_method_id")
    return truck, df


truck, df = load_data()

# Fixed domain keeps each truck's colour the same across charts and filters.
truck_colors = alt.Scale(domain=sorted(truck["truck_name"]))
st.title("Food Truck Performance")

# Filters
truck_col, time_col, date_col = st.columns([3, 3, 2])
selected_trucks = truck_col.multiselect(
    "Trucks", truck["truck_name"].tolist(), default=truck["truck_name"].tolist()
)
time_range = time_col.radio(
    "Time Range", ["Yesterday", "Last Week", "All Time", "Custom Range"], horizontal=True
)

min_date, max_date = df["at"].dt.date.min(), df["at"].dt.date.max()
df = df[df["truck_name"].isin(selected_trucks)]

# Relative windows are anchored to the latest transaction, not the current time.
today = df["at"].max().normalize() if not df.empty else pd.Timestamp.now().normalize()
if time_range == "Last Week":
    # Previous calendar week, Monday 00:00 up to (excluding) this week's Monday.
    this_monday = today - pd.Timedelta(days=today.weekday())
    df = df[(df["at"] >= this_monday - pd.Timedelta(days=7)) &
            (df["at"] < this_monday)]
elif time_range == "Yesterday":
    # The calendar day before the latest transaction's day.
    df = df[(df["at"] >= today - pd.Timedelta(days=1)) & (df["at"] < today)]
elif time_range == "Custom Range":
    # Starts from the range last shown by a non-custom option.
    date_range = date_col.date_input(
        "Date Range", st.session_state.get("last_range", (min_date, max_date)),
        min_value=min_date, max_value=max_date
    )
    if len(date_range) == 2:
        df = df[(df["at"].dt.date >= date_range[0]) &
                (df["at"].dt.date <= date_range[1])]

if time_range != "Custom Range":
    # Disabled picker shows the range of the data actually displayed.
    shown = (df["at"].dt.date.min(), df["at"].dt.date.max()
             ) if not df.empty else (min_date, max_date)
    st.session_state["last_range"] = shown
    date_col.date_input("Date Range", shown, min_value=min_date,
                        max_value=max_date, disabled=True)

if df.empty:
    st.warning("No transactions match the selected filters.")
    st.stop()

# Headline metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Revenue", f"£{df['total'].sum():,.2f}")
col2.metric("Transactions", f"{len(df):,}")
col3.metric("Average Transaction", f"£{df['total'].mean():,.2f}")

# Per-truck performance
by_truck = (
    df.groupby(["truck_name", "truck_description",
               "has_card_reader", "fsa_rating"])
    .agg(revenue=("total", "sum"), transactions=("transaction_id", "count"), avg_total=("total", "mean"))
    .reset_index()
    .sort_values("revenue", ascending=False)
    .set_index("truck_name")
)

overview_tab, trends_tab, values_tab, payments_tab = st.tabs(
    ["Overview", "Trends", "Transaction Values", "Payments"])

with overview_tab:
    st.subheader("Share of Revenue by Truck")
    revenue_share = by_truck.reset_index()[["truck_name", "revenue"]]
    st.altair_chart(
        alt.Chart(revenue_share).mark_arc().encode(
            theta=alt.Theta("revenue:Q", title="Revenue (£)"),
            color=alt.Color("truck_name:N", title="Truck", scale=truck_colors),
            tooltip=[alt.Tooltip("truck_name:N", title="Truck"),
                     alt.Tooltip("revenue:Q", title="Revenue (£)", format=",.2f")],
        ),
        use_container_width=True,
    )

    left, right = st.columns(2)
    left.subheader("Revenue by Truck")
    left.altair_chart(static_chart(by_truck[["revenue"]], "bar", "N", "Truck", "Revenue (£)", color_scale=truck_colors),
                      use_container_width=True)
    right.subheader("Transactions by Truck")
    right.altair_chart(static_chart(by_truck[["transactions"]], "bar", "N", "Truck", "Transactions", color_scale=truck_colors),
                       use_container_width=True)

with trends_tab:
    # Revenue over time per truck (hourly for a single day, otherwise daily)
    hourly = time_range == "Yesterday"
    st.subheader("Hourly Revenue" if hourly else "Daily Revenue")
    period = df["at"].dt.floor(
        "h") if hourly else pd.to_datetime(df["at"].dt.date)
    daily = (
        df.assign(day=period)
        .pivot_table(index="day", columns="truck_name", values="total", aggfunc="sum")
        .fillna(0)
    )
    time_label = "Hour" if hourly else "Date"
    st.altair_chart(static_chart(daily, "line", "T", time_label, "Revenue (£)", "Truck", truck_colors),
                    use_container_width=True)

    st.subheader("Revenue by Hour and Weekday")
    weekdays = ["Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data = (
        df.assign(weekday=df["at"].dt.day_name(), hour=df["at"].dt.hour)
        .groupby(["weekday", "hour"], as_index=False)["total"].sum()
    )
    st.altair_chart(
        alt.Chart(heatmap_data).mark_rect().encode(
            x=alt.X("hour:O", title="Hour of Day"),
            y=alt.Y("weekday:N", title="Day of Week", sort=weekdays),
            color=alt.Color("total:Q", title="Revenue (£)",
                            scale=alt.Scale(scheme="blues")),
            tooltip=[alt.Tooltip("weekday:N", title="Day"),
                     alt.Tooltip("hour:O", title="Hour"),
                     alt.Tooltip("total:Q", title="Revenue (£)", format=",.2f")],
        ),
        use_container_width=True,
    )

with values_tab:
    left, right = st.columns(2)
    left.subheader("Transaction Totals by Truck")
    box_data = df[["truck_name", "total"]].assign(
        label=df["truck_name"].map(wrap_label))
    left.altair_chart(
        alt.Chart(box_data).mark_boxplot().encode(
            x=alt.X("label:N", title="Truck", axis=WRAPPED_AXIS),
            y=alt.Y("total:Q", title="Transaction Total (£)"),
            color=alt.Color("truck_name:N", scale=truck_colors, legend=None),
        ),
        use_container_width=True,
    )
    right.subheader("Average Transaction by Truck")
    right.altair_chart(static_chart(by_truck[["avg_total"]], "bar", "N", "Truck", "Average Transaction (£)", color_scale=truck_colors),
                       use_container_width=True)

with payments_tab:
    st.subheader("Payment Methods")
    payments = df.pivot_table(
        index="truck_name", columns="payment_method", values="total", aggfunc="sum"
    ).fillna(0)
    st.altair_chart(static_chart(payments, "bar", "N", "Truck", "Revenue (£)", "Payment Method"),
                    use_container_width=True)

    st.subheader("Transaction Totals by Payment Method")
    st.altair_chart(
        alt.Chart(df[["payment_method", "total"]]).mark_boxplot().encode(
            x=alt.X("payment_method:N", title="Payment Method",
                    axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total:Q", title="Transaction Total (£)"),
            color=alt.Color("payment_method:N", legend=None),
        ),
        use_container_width=True,
    )
