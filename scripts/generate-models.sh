#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

REPO=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

MODEL="${REPO}/seguro/commands/scheduler/compose_model.py"

cat > "${MODEL}" <<EOF
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0
# flake8: noqa

EOF

poetry run datamodel-codegen  \
    --url https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json \
    --input-file-type jsonschema >> "${MODEL}"
