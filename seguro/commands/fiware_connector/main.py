# SPDX-FileCopyrightText: 2025 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import argparse
import datetime
from functools import partial
import json
import logging
import os
import time
from typing import Union

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

CONNECTOR_ID = env.str("CONNECTOR_ID", "fiware-connector")

MAPPING_JSON = env.str("MAPPING_JSON", None)

FORMAT_STRING = (
    "{timestamp}|"
    + "dateObservedFrom|{dateObservedFrom}|"
    + "phaseVoltage|{phaseVoltage}|"
    + "current|{phaseCurrent}|"
    + "apparentPower|{apparentPower}|"
    + "frequency|{frequency}"
)


def post_sample(
    session: requests.Session,
    url: str,
    identifier: str,
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

    logging.debug("[%s] Sending message: %s", identifier, message)
    # return True
    return session.post(
        url,
        data=message,
        timeout=5,
        cert=(FIWARE_TLS_CERT, FIWARE_TLS_KEY),
        params=[("k", API_KEY), ("i", identifier)],
    )


def convert_complex(complexVal: complex) -> dict:
    return {
        "re": complexVal.real,
        "im": complexVal.imag,
    }


def prettify_identifier(
    topic: str, sample_index: int, identifier_map: Union[dict, None]
) -> str:
    if (
        identifier_map is not None
        and f"{topic}/currentgroup{sample_index}" in identifier_map
    ):
        return identifier_map[f"{topic}/currentgroup{sample_index}"]
    return f"{topic}/currentgroup{sample_index}"


def flatten_dict(nested_dict: dict, separator="/") -> dict:
    flat_dict = {}

    def _flatten(obj, name=""):
        if isinstance(obj, dict):
            for key in obj:
                _flatten(obj[key], name + key + separator)
        else:
            flat_dict[name[:-1]] = obj

    _flatten(nested_dict)

    logging.debug("Flattened dict: %s", flat_dict)

    return flat_dict


def parse_identfier_map(mapping: str = MAPPING_JSON) -> dict:
    if mapping is not None:
        if os.path.exists(mapping):
            with open(mapping, encoding="utf-8") as file:
                return flatten_dict(json.load(file))

    return flatten_dict(json.loads(mapping))


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

    def callback(
        session: requests.Session,
        identifier_map: Union[dict, None],
        b: broker.Client,
        topic: str,
        samples: list[Sample],
    ):
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

        sample_index = 1
        sample_start = 3  # First three elements are always the voltages
        sample_end = len(samples[-1].data) - 1
        curr_end = sample_start + 6

        while curr_end <= sample_end:
            # Note: This currently does not send incomplete samples.
            # I.e., at least 3 Currents and 3 Power values have to be present.
            sample_range = list(range(sample_start, curr_end))

            ret = post_sample(
                session,
                URL,
                prettify_identifier(topic, sample_index, identifier_map),
                samples[-1].ts_origin,
                json.dumps(  # Voltage
                    {
                        "L1": convert_complex(samples[-1].data[0]),
                        "L2": convert_complex(samples[-1].data[1]),
                        "L3": convert_complex(samples[-1].data[2]),
                    },
                    separators=(",", ":"),
                ),
                json.dumps(  # Current
                    {
                        "L1": convert_complex(
                            samples[-1].data[sample_range[0]]
                        ),
                        "L2": convert_complex(
                            samples[-1].data[sample_range[1]]
                        ),
                        "L3": convert_complex(
                            samples[-1].data[sample_range[2]]
                        ),
                    },
                    separators=(",", ":"),
                ),
                json.dumps(  # Power
                    {
                        "L1": convert_complex(
                            samples[-1].data[sample_range[3]]
                        ),
                        "L2": convert_complex(
                            samples[-1].data[sample_range[4]]
                        ),
                        "L3": convert_complex(
                            samples[-1].data[sample_range[5]]
                        ),
                    },
                    separators=(",", ":"),
                ),
                samples[-1].data[-1],  # Frequency
            )

            sample_start = curr_end
            curr_end += 6
            sample_index += 1

            logging.debug(ret.text)

    b = broker.Client(CONNECTOR_ID)
    session = requests.Session()
    identifier_map = (
        None if MAPPING_JSON is None else parse_identfier_map(MAPPING_JSON)
    )

    for topic in TOPIC.split(","):
        b.subscribe_samples(topic, partial(callback, session, identifier_map))

    logging.info("Subscribed to %s", TOPIC)
    logging.info("FIWARE URL: %s/?k=%s&i=%s", URL, API_KEY, "<topic>")

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    main()
