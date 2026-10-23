"""AWS Lambda that builds an HTML report of one day's transactions.

The day is taken from the event's `date` key, or the `date` query string
parameter, as YYYY-MM-DD. It defaults to today's date in UK time.

Returns a dict with two keys:
    subject   Email subject, "Daily Report <DATE>".
    html      The HTML report body.

Environment variables:
    GLUE_DATABASE            Glue database containing the transactions, truck and
                             payment_method tables.
    ATHENA_OUTPUT_LOCATION   S3 location Athena writes query results to.
    ATHENA_WORKGROUP         Athena workgroup (optional, defaults to "primary").
"""

import logging
import sys
import time
from collections import defaultdict
from datetime import datetime
from html import escape
from os import environ
from pathlib import Path
from zoneinfo import ZoneInfo

import boto3

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is only needed for local runs; Lambda sets env vars itself
    pass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

POLL_INTERVAL_SECONDS = 1
QUERY_TIMEOUT_SECONDS = 60


athena = boto3.client("athena", region_name=environ["REGION"])

if environ.get("LOCAL_TEST"):
    athena = boto3.client("athena", region_name=environ["REGION"],
                          # `docker run --env-file` keeps the quotes from .env values
                          aws_access_key_id=environ["ACCESS_KEY"].strip("\"'"),
                          aws_secret_access_key=environ["SECRET_ACCESS_KEY"].strip("\"'"))


class InvalidDateError(ValueError):
    """Raised when the requested date is not a valid YYYY-MM-DD string."""


def get_requested_date(event: dict) -> str:
    """Returns the validated report date from the event, defaulting to today (UK time)."""
    params = event.get("queryStringParameters") or {}
    value = event.get("date") or params.get("date")

    if not value:
        return datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d")

    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as err:
        raise InvalidDateError(
            f"Invalid date {value!r}, expected YYYY-MM-DD") from err


def run_query(sql: str) -> list[dict]:
    """Runs a query in Athena, waits for it and returns the rows as dicts."""
    execution = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": environ["GLUE_DATABASE"]},
        ResultConfiguration={
            "OutputLocation": environ["ATHENA_OUTPUT_LOCATION"]},
        WorkGroup=environ.get("ATHENA_WORKGROUP", "primary"),
    )
    query_id = execution["QueryExecutionId"]

    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_id)[
            "QueryExecution"]["Status"]
        state = status["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(
                f"Athena query {state}: {status.get('StateChangeReason', 'unknown reason')}")
        if time.monotonic() > deadline:
            athena.stop_query_execution(QueryExecutionId=query_id)
            raise TimeoutError("Athena query timed out")
        time.sleep(POLL_INTERVAL_SECONDS)

    rows = []
    columns = None
    paginator = athena.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=query_id):
        for row in page["ResultSet"]["Rows"]:
            values = [field.get("VarCharValue") for field in row["Data"]]
            # The first row of the first page is the header
            if columns is None:
                columns = values
                continue
            rows.append(dict(zip(columns, values)))
    return rows


def fetch_transactions(date: str) -> list[dict]:
    """Fetches the transactions for a day (YYYY-MM-DD), joined to truck and payment method."""
    # `date` has been validated by get_requested_date so is safe to inline
    sql = f"""
        SELECT t.transaction_id, CAST(t."at" AS varchar) AS "at", t.total,
               tr.truck_name, p.payment_method
        FROM transactions t
        JOIN truck tr ON t.truck_id = tr.truck_id
        JOIN payment_method p ON t.payment_method_id = p.payment_method_id
        WHERE CAST(t."date" AS varchar) = '{date}'
        ORDER BY t."at"
    """
    transactions = run_query(sql)
    for transaction in transactions:
        transaction["total"] = float(transaction["total"])
    return transactions


def money(value: float) -> str:
    return f"£{value:,.2f}"


def group_totals(transactions: list[dict], key) -> list[tuple[str, int, float]]:
    """Returns (group, transaction count, revenue) tuples, highest revenue first."""
    groups = defaultdict(lambda: [0, 0.0])
    for transaction in transactions:
        group = groups[key(transaction)]
        group[0] += 1
        group[1] += transaction["total"]
    return sorted(((name, count, revenue) for name, (count, revenue) in groups.items()),
                  key=lambda item: item[2], reverse=True)


def render_table(headers: list[str], rows: list[list[str]], numeric_from: int = 1) -> str:
    """Renders an HTML table, escaping every cell. Columns (and their headers) from numeric_from are right-aligned."""
    head = "".join(
        f'<th class="num">{escape(h)}</th>' if i >= numeric_from
        else f"<th>{escape(h)}</th>"
        for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(
            f'<td class="num">{escape(str(cell))}</td>' if i >= numeric_from
            else f"<td>{escape(str(cell))}</td>"
            for i, cell in enumerate(row)) + "</tr>"
        for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_report(date: str, transactions: list[dict]) -> str:
    """Builds the full HTML document for a day's transactions."""
    title = f"Transaction Report - {date}"

    if not transactions:
        content = "<p>No transactions were found for this day.</p>"
    else:
        totals = [t["total"] for t in transactions]
        revenue = sum(totals)
        # Performance is judged by total revenue; group_totals sorts highest first
        by_truck = group_totals(transactions, lambda t: t["truck_name"])
        best_truck, worst_truck = by_truck[0], by_truck[-1]
        summary = "".join(
            f'<div class="card"><span class="label">{escape(label)}</span>'
            f'<span class="value">{escape(value)}</span>'
            + (f'<span class="detail">{escape(detail)}</span>' if detail else "")
            + "</div>"
            for label, value, detail in [
                ("Transactions", f"{len(transactions):,}", ""),
                ("Total Revenue", money(revenue), ""),
                ("Average Transaction", money(revenue / len(transactions)), ""),
                ("Largest Transaction", money(max(totals)), ""),
                ("Smallest Transaction", money(min(totals)), ""),
                ("Highest Performing Truck", best_truck[0],
                 f"{money(best_truck[2])} revenue"),
                ("Lowest Performing Truck", worst_truck[0],
                 f"{money(worst_truck[2])} revenue"),
            ])

        def breakdown(heading: str, label: str, key, chronological: bool = False) -> str:
            groups = group_totals(transactions, key)
            if chronological:
                groups.sort(key=lambda group: group[0])
            rows = [[name, f"{count:,}", money(rev), money(rev / count)]
                    for name, count, rev in groups]
            return f"<h2>{escape(heading)}</h2>" + render_table(
                [label, "Transactions", "Revenue", "Average Transaction"], rows)

        content = (
            f'<div class="cards">{summary}</div>'
            + breakdown("Revenue by Truck", "Truck", lambda t: t["truck_name"])
            + breakdown("Revenue by Payment Method", "Payment Method",
                        lambda t: t["payment_method"])
            + breakdown("Revenue by Hour", "Hour",
                        lambda t: t["at"][11:13] + ":00", chronological=True)
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; color: #222; padding: 0 1rem; }}
  h1 {{ border-bottom: 2px solid #444; padding-bottom: .5rem; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }}
  .card {{ flex: 1 1 150px; background: #f3f5f7; border-radius: 6px; padding: 1rem; }}
  .label {{ display: block; font-size: .8rem; color: #555; }}
  .value {{ font-size: 1.4rem; font-weight: bold; }}
  .detail {{ display: block; font-size: .8rem; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
  th, td {{ border-bottom: 1px solid #ddd; padding: .4rem .6rem; text-align: left; }}
  th {{ background: #444; color: #fff; }}
  th.num, td.num {{ text-align: right; }}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
{content}
</body>
</html>"""


def lambda_handler(event: dict, context=None) -> dict:
    """Lambda entry point: returns the email subject and HTML report for the requested day."""
    date = get_requested_date(event or {})

    try:
        transactions = fetch_transactions(date)
    except Exception:
        logger.exception("Failed to build report for %s", date)
        raise

    logger.info("Building report for %s with %d transactions",
                date, len(transactions))
    return {
        "subject": f"Daily Report {date}",
        "html": build_report(date, transactions),
    }


if __name__ == "__main__":
    # Usage: python report.py [YYYY-MM-DD]
    logging.basicConfig(level=logging.INFO)
    event = {"date": sys.argv[1]} if len(sys.argv) > 1 else {}

    try:
        result = lambda_handler(event)
    except Exception as err:
        sys.exit(f"Report failed: {err}")

    report_date = get_requested_date(event)
    output_path = Path(__file__).parent / f"report_{report_date}.html"
    output_path.write_text(result["html"], encoding="utf-8")
    print(f"Subject: {result['subject']}")
    print(f"Report written to {output_path}")
