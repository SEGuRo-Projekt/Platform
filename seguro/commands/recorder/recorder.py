# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import logging
import math
from pathlib import Path
import pandas as pd

from seguro.common import store
from villas.node.sample import Sample


class Recorder:
    def __init__(self, s: store.Client, topic: str):
        self.path = Path(topic)

        logger_name = ".".join(["recorder"] + topic.split("/")[1:])
        self.logger = logging.getLogger(logger_name)

        self.store = s

        self.samples: list[Sample]
        self.max_values: int

        self._reset()

    def record_samples(self, samples: list[Sample]):
        """

        Args:
          samples: A list of samples which should be appended to the
                   current frame

        """
        self.logger.debug("Recording %d samples", len(samples))

        for sample in samples:
            if sample.new_frame:
                self._write_frame()

            self.samples.append(sample)
            self.max_values = max(self.max_values, len(sample.data))

    def _write_frame(self):
        if len(self.samples) == 0:
            return

        self.logger.info(
            "Writing frame object containing %d samples",
            len(self.samples),
        )

        index = [
            pd.Timestamp(
                sample.ts_origin.seconds * 1000000000
                + sample.ts_origin.nanoseconds
            )
            for sample in self.samples
        ]
        data = {"sequence": [sample.sequence for sample in self.samples]}

        for i in range(self.max_values):
            if isinstance(self.samples[0].data[i], complex):
                data.update({
                    f"signal{i}.real": [
                        smp.data[i].real if i < len(smp.data) else math.nan
                        for smp in self.samples
                    ],
                    f"signal{i}.imag": [
                        smp.data[i].imag if i < len(smp.data) else math.nan
                        for smp in self.samples
                    ],
                })

            else:
                data.update({
                    f"signal{i}": [
                        smp.data[i] if i < len(smp.data) else math.nan
                        for smp in self.samples
                    ]
                })

        df = pd.DataFrame(data, index)

        ts = self.samples[0].ts_origin.datetime()
        ts = ts.replace(microsecond=0)
        obj_path = self.path / f"{ts.isoformat()}.parquet"

        self.store.put_frame(obj_path.as_posix(), df)

        self._reset()

    def _reset(self):
        self.samples = []
        self.max_values = 0
