# Configuration file for the Sphinx documentation builder.
#
# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
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

project = "SEGuRo Platform"
copyright = "2024, The SEGuRo project partners"
author = "The SEGuRo project partners"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.linkcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    # "sphinxcontrib.autodoc_pydantic",
    "sphinxext.opengraph",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
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
html_css_files = ["styles/custom.css"]
html_js_files = ["scripts/custom.js"]
html_title = "SEGuRo Platform"
html_theme_options = {
    "source_repository": "https://github.com/SEGuRo-Projekt/Platform/",
    "source_branch": "main",
    "source_directory": "docs/",
    "announcement": "This is a preview version! The platform is currently in its alpha phase of its software release life cycle.",  # noqa E501
    "light_css_variables": {
        "color-brand-primary": "#ad2f24",
        "color-brand-content": "#7C4DFF",
    },
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/SEGuRo-Projekt/Platform/",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,  # noqa E501
            "class": "",
        },
    ],
}


exclude_patterns = ["test_**.py"]

# Auto API
autosummary_generate = True

autodoc_typehints = "description"

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

autodoc_pydantic_model_show_json = True
autodoc_pydantic_settings_show_json = True
autodoc_pydantic_model_erdantic_figure = False
autodoc_pydantic_model_erdantic_figure_collapsed = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_config_summary = False

# Link code
commit = "master"
code_url = f"https://github.com/SEGuRo-Projekt/Platform/blob/{commit}"


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
    except Exception:
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
