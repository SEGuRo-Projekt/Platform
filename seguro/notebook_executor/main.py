# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import os.path
import sys

import nbformat
from nbconvert import PDFExporter
from nbconvert.preprocessors import ExecutePreprocessor

from seguro.common import store, job


def main() -> int:
    client = store.Client()

    if job.info.triggered_by.event != "created":
        return -1

    nb_obj = job.info.notebook

    # Fetch Notebook from store
    nb_contents = client.get_file_contents(nb_obj).read()

    # Read Notebook
    nb = nbformat.reads(nb_contents, as_version=4)

    # Execute Notebook
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb)

    # Export Notebook as PDF file
    pexp = PDFExporter()
    resp = pexp.from_notebook_node(nb)

    pre, _ = os.path.splitext(nb_obj)
    pdf_obj = pre + ".pdf"

    client.put_file_contents(pdf_obj, resp[0])

    return 0


if __name__ == "__main__":
    sys.exit(main())
