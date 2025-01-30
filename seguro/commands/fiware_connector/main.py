# SPDX-FileCopyrightText: 2025 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import argparse
import datetime
import json
import logging
import time

import environ
import requests  # type: ignore

from villas.node.formats import Sample

from seguro.common import broker, config


env = environ.Env()

URL = env.str("FIWARE_URL", None)
API_KEY = env.str("API_KEY", None)
TOPIC = env.str("TOPIC", None)

FIWARE_TLS_CERT = env.str("FIWARE_TLS_CERT", None)
FIWARE_TLS_KEY = env.str("FIWARE_TLS_KEY", None)

ID = env.str("ID", "loc1/md1/mp1")

FORMAT_STRING = (
    "{timestamp}|"
    + "dateObservedFrom|{dateObservedFrom}|"
    + "phaseVoltage|{phaseVoltage}|"
    + "current|{phaseCurrent}|"
    + "apparentPower|{apparentPower}|"
    + "frequency|{frequency}"
)


def post_sample(
    url: str,
    sample_ts: str,
    voltage: str,
    current: str,
    power: str,
    freq: float,
) -> requests.Response:
    def convert_timestamp(ts) -> str:
        dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(
            seconds=ts.seconds, microseconds=ts.nanoseconds / 1000
        )
        return dt.isoformat()

    message = (
        FORMAT_STRING.strip()
        .format(
            timestamp=datetime.datetime.now().isoformat(),
            dateObservedFrom=convert_timestamp(sample_ts),
            phaseVoltage=voltage,
            phaseCurrent=current,
            apparentPower=power,
            frequency=freq,
        )
        .encode()
    )

    return requests.post(
        url,
        data=message,
        timeout=5,
        cert=(FIWARE_TLS_CERT, FIWARE_TLS_KEY),
        params=[("k", API_KEY), ("i", ID)],
    )


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    def callback(b: broker.Client, topic: str, samples: list[Sample]):
        """Callback which gets called for each received MQTT message.

        Args:
            client: The broker client
            msg: The MQTT message

        """
        logging.debug(
            "%s, %s - %s - %s%s",
            samples[-1].ts_origin.seconds,
            samples[-1].ts_origin.nanoseconds,
            topic,
            samples[-1].data,
            samples[-1],
        )

        ret = post_sample(
            URL,
            samples[0].ts_origin,
            json.dumps(  # Voltage
                {
                    "L1": str(samples[-1].data[0]),
                    "L2": str(samples[-1].data[1]),
                    "L3": str(samples[-1].data[2]),
                },
                separators=(",", ":"),
            ),
            json.dumps(  # Current
                {
                    "L1": str(samples[-1].data[3]),
                    "L2": str(samples[-1].data[4]),
                    "L3": str(samples[-1].data[5]),
                },
                separators=(",", ":"),
            ),
            json.dumps(  # Power
                {
                    "L1": str(samples[-1].data[6]),
                    "L2": str(samples[-1].data[7]),
                    "L3": str(samples[-1].data[8]),
                },
                separators=(",", ":"),
            ),
            samples[-1].data[9],  # Frequency
        )

        logging.debug(ret.text)

    b = broker.Client(f"fiware-connector-{ID}")

    b.subscribe_samples(TOPIC, callback)

    logging.info("Subscribed to %s", TOPIC)
    logging.info("FIWARE URL: %s/?k=%s&i-%s", URL, API_KEY, ID)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    main()
