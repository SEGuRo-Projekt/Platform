# Configuration file for the Sphinx documentation builder.
#
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib
import inspect

# Fix sys.path for autodoc
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "SEGuRo Plattform"
copyright = "2024, The SEGuRo project partners"
author = "The SEGuRo project partners"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.intersphinx",
    "sphinx.ext.linkcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    # "sphinxcontrib.bibtex",
    "sphinxext.opengraph",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
    "autoapi.extension",
    "myst_parser",
]

templates_path = ["_templates"]

language = "en"

# bibtex_bibfiles = []

# Open Graph
ogp_site_url = "https://seguro.eonerc.rwth-aachen.de/"
ogp_description_length = 300
ogp_type = "article"

ogp_custom_meta_tags = [
    '<meta property="og:ignore_canonical" content="true" />',
]

ogp_enable_meta_description = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["custom.css"]


exclude_patterns = ["test_**.py"]

# Auto API
autodoc_typehints = "description"

autoapi_add_toctree_entry = False
autoapi_dirs = ["../seguro"]
autoapi_options = [
    "members",
    "undoc-members",
    "private-members",
    "show-inheritance",
    "show-inheritance-diagram",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_ignore = ["*migrations*", "*/test_*"]


# Link code
commit = "master"
code_url = f"https://github.com/SEGuRo-Projekt/Plattform/blob/{commit}"


def linkcode_resolve(domain, info):
    assert domain == "py", "expected only Python objects"

    mod = importlib.import_module(info["module"])
    if "." in info["fullname"]:
        objname, attrname = info["fullname"].split(".")
        obj = getattr(mod, objname)
        try:
            obj = getattr(obj, attrname)
        except AttributeError:
            return None
    else:
        obj = getattr(mod, info["fullname"])

    try:
        file = inspect.getsourcefile(obj)
        lines = inspect.getsourcelines(obj)
    except TypeError:
        return None

    if file is None:
        return None

    file = os.path.relpath(file, os.path.abspath("."))
    if not file.startswith("seguro"):
        return None

    start, end = lines[1], lines[1] + len(lines[0]) - 1

    return f"{code_url}/{file}#L{start}-L{end}"


def is_spdx_header(line: str):
    return not line.lstrip().startswith("SPDX-")


def remove_spdx_headers(app, what, name, obj, options, lines: list[str]):
    if what == "module":
        lines[:] = list(filter(is_spdx_header, lines))


def setup(app):
    app.connect("autodoc-process-docstring", remove_spdx_headers)
