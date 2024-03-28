# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys

from seguro.common import store


def main() -> int:
    client = store.Client()

    filename = "data/md1/mp1"

    frame = client.get_frame(filename)

    frame *= 2

    client.put_frame(filename + "_scaled", frame)

    return 0


if __name__ == "__main__":
    sys.exit(main())
