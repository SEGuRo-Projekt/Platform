# SPDX-FileCopyrightText: 2026 Henrik Hörter
# SPDX-License-Identifier: Apache-2.0
import argparse
import re
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path

from seguro.common import store
from seguro.common import config
from seguro.commands.s3_tool.main import push, pull, remove, list_elements
from seguro.common.store import Client

LOCAL_TMP = ".LOCAL/"
REMOTE_FOLDER = "data/measurements/demo-data/"


def get_time(args):
    print(datetime.fromisoformat(args.at))
    print(type(args.at))


def resolve_timeframe(start_input: str, end_or_duration) -> tuple[datetime, datetime]:

    start_dt = datetime.fromisoformat(start_input)

    if start_dt.tzinfo is None:  # check for timezone information TODO: SO FAR ALL OBJECTS ARE UTC +00 ??
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if isinstance(end_or_duration, timedelta):
        end_dt = start_dt + end_or_duration  # is duration
    else:
        end_dt = datetime.fromisoformat(end_or_duration)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

    return start_dt, end_dt


def fetch_candidates(start_dt: datetime, end_dt: datetime) -> list[str]:
    """
    Fetches candidate object keys from MinIO within [start_dt, end_dt] lexicographical bounds.
    Stops requesting additional pages as soon as an object key exceeds end_dt.
    """

    s = Client()

    start_after_key = f"{REMOTE_FOLDER}{start_dt.isoformat()}.parquet"
    end_key = f"{REMOTE_FOLDER}{end_dt.isoformat()}.parquet"

    objects = s.client.list_objects(
        bucket_name=s.bucket,
        prefix=REMOTE_FOLDER,
        start_after=start_after_key,
    )

    candidate_keys = []

    for object in objects:
        key = object.object_name
        # EXIT LIMIT: Stop as soon as keys exceed end_dt
        # Breaking out of this loop prevents MinIO from requesting further pages
        if key > end_key:
            break

        candidate_keys.append(key)

    return candidate_keys


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


def get_files(candidates: list[str]):  # TODO: fix pull function to accept lists?

    s = Client()
    if not Path(LOCAL_TMP).is_dir():  # TODO: remove probably, setup new everytime
        Path(LOCAL_TMP).mkdir()

    for candidate in candidates:
        pull_args = argparse.Namespace(localfile=LOCAL_TMP, remotefile=candidate, globbing=False)
        pull(s, pull_args)


def authenticate_files(): ...


def merge_files(): ...


def parquet_merger(args):

    if args.end is not None and args.duration is None:
        start_dt, end_dt = resolve_timeframe(args.start, args.end)

    if args.end is None and args.duration is not None:
        start_dt, end_dt = resolve_timeframe(args.start, parse_duration(args.duration))

    print(f"start: {start_dt.isoformat()}, end: {end_dt.isoformat()}")

    candidates = fetch_candidates(start_dt, end_dt)

    for candidate in candidates:
        print(candidate)

    # TODO pull candidates
    get_files(candidates)

    # TODO authenticate files

    # TODO merge files

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

    parser.set_defaults(func=parquet_merger)

    args = parser.parse_args()

    if args.end is None and args.duration is None:
        parser.error("Use either --end or --duration, not both.")

    return args.func(args)
