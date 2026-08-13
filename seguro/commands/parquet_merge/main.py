# SPDX-FileCopyrightText: 2026 Henrik Hörter
# SPDX-License-Identifier: Apache-2.0
import argparse
import re
from datetime import datetime, date, time, timedelta

from seguro.common import store
from seguro.common import config
from seguro.commands.s3_tool.main import push, pull, remove
from seguro.common.store import Client

LOCAL_TMP = ".LOCAL/"


def get_time(args):
    print(datetime.fromisoformat(args.at))
    print(type(args.at))


def parse_duration(value: str) -> timedelta:
    matches = re.findall(r"(\d+)(d|h|min|s)", value)

    if not matches:
        raise ValueError("Duration must look like '5h', '30min', '1h30min', or '2d4h15min'")

    total = timedelta()

    for amount_str, unit in matches:
        amount = int(amount_str)

        if unit == "d":
            total += timedelta(days=amount)
        elif unit == "h":
            total += timedelta(hours=amount)
        elif unit == "min":
            total += timedelta(minutes=amount)
        elif unit == "s":
            total += timedelta(seconds=amount)
    return total


def get_files(startdate: datetime, enddate: datetime):

    s = Client()

    args = argparse.Namespace()

    if enddate - startdate < timedelta(minutes=1):
        # construct args to pull startdate minute and enddate minuts
        startdate_prefix = startdate.strftime("%Y-%m-%dT%H:%M")
        print(f"start: {startdate_prefix}")
        start_args = argparse.Namespace(
            localfile=LOCAL_TMP + ".", remotefile="data/measurements/demo-data/" + startdate_prefix + "*", globbing=True
        )
        pull(s, start_args)

        enddate_prefix = enddate.strftime("%Y-%m-%dT%H:%M")
        print(f"end: {enddate_prefix}")
        end_args = argparse.Namespace(
            localfile=LOCAL_TMP + ".", remotefile="data/measurements/demo-data/" + enddate_prefix + "*", globbing=True
        )
        pull(s, end_args)

    elif enddate - startdate < timedelta(hours=1):
        # construct args to pull startdate hour and enddate hour
        ...
    elif enddate - startdate < timedelta(days=1):
        # construct args to pull startdate day and enddate day
        ...
    else:  # multiday
        ...
    # localfile=LOCAL_TMP + "demo1",
    # remotefile="data/measurements/demo-data/" + startdate.isoformat() + ".parquet",
    # globbing=False,

    # pull(s, args)


def merge_files(args):

    if args.end is not None and args.duration is None:
        enddate = datetime.fromisoformat(args.end)

    if args.end is None and args.duration is not None:
        enddate = datetime.fromisoformat(args.start) + parse_duration(args.duration)

    startdate = datetime.fromisoformat(args.start)

    get_files(startdate, enddate)

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="parquet_merge", description="Combine multiple data files in parquet format to one file"
    )

    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    parser.add_argument("-s", "--start", required=True, type=str, help="Start-Timestamp in ISO 8601 format")

    group = parser.add_mutually_exclusive_group(required=True)  # allows to either have --end or --duration flag
    group.add_argument("-e", "--end", type=str, help="End-Timestamp in ISO 8601 format")
    group.add_argument("-d", "--duration", type=str, help="Duration starting from start-timestamp")

    parser.set_defaults(func=merge_files)

    args = parser.parse_args()

    if args.end is None and args.duration is None:
        parser.error("Use either --end or --duration, not both.")

    return args.func(args)
