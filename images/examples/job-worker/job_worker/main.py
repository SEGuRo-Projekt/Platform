# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys

from seguro.common import store


def main() -> int:
    s = store.Client()

    filename = "data/md1/mp1"

    frame = s.get_frame(filename)

    frame *= 2

    s.put_frame(filename + "_scaled", frame)

    return 0


if __name__ == "__main__":
    sys.exit(main())
