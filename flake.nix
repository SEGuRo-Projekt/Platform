# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0
{
  description = "Application packaged using poetry2nix";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      poetry2nix,
    }:
    let
      poetryOverrrides =
        final: prev:
        let
          # Workaround https://github.com/nix-community/poetry2nix/issues/568
          addBuildInputs =
            name: buildInputs:
            prev.${name}.overridePythonAttrs (old: {
              buildInputs = (builtins.map (x: prev.${x}) buildInputs) ++ (old.buildInputs or [ ]);
            });
          mkOverrides = prev.lib.mapAttrs (name: value: addBuildInputs name value);
        in
        mkOverrides {
          aws-logging-handlers = [ "setuptools" ];
          villas-node = [ "setuptools" ];
          types-python-slugify = [ "setuptools" ];
          paho-mqtt = [ "hatchling" ];
          dnspython = [ "hatchling" ];
          pyxlsb = [ "setuptools" ];
          rfc3161ng = [ "setuptools" ];
          datamodel-code-generator = [ "poetry-core" ];
        }
        // {
          python-calamine = prev.python-calamine.override { preferWheel = true; };
          apprise = prev.apprise.override { preferWheel = true; };
          pandas = prev.pandas.override { preferWheel = true; };
          mypy = prev.mypy.override { preferWheel = true; };
          pyzmq = prev.pyzmq.override { preferWheel = true; };
        };

      packagesOverlay = final: prev: {
        seguro-platform = final.poetry2nix.mkPoetryApplication {
          projectDir = ./.;
          groups = [ "dev" ];
          overrides = final.poetry2nix.overrides.withDefaults poetryOverrrides;
        };
      };

      overlays = {
        default = nixpkgs.lib.composeExtensions poetry2nix.overlays.default packagesOverlay;
      };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = builtins.attrValues overlays;
        };

        env = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          groups = [ "jupyter" ];
          editablePackageSources = {
            seguro-platform = ./seguro;
          };
          overrides = pkgs.poetry2nix.overrides.withDefaults poetryOverrrides;
        };
      in
      {
        packages = rec {
          inherit (pkgs) seguro-platform;
          default = seguro-platform;
        };

        devShells = rec {
          seguro-platform = pkgs.mkShell {
            inputsFrom = [ pkgs.seguro-platform ];

            buildInputs = [ pkgs.graphviz ];

            packages = with pkgs; [
              mypy
              poetry
              env
              mosquitto
              graphviz

              (pkgs.poetry2nix.mkPoetryScriptsPackage { projectDir = ./.; })

              # For notebook_executor
              # See: https://github.com/jupyter/nbconvert/issues/1328#issuecomment-1768665936
              (texliveSmall.withPackages (
                ps: with ps; [
                  amsmath
                  booktabs
                  caption
                  collectbox
                  collection-fontsrecommended
                  adjustbox
                  ec
                  enumitem
                  environ
                  etoolbox
                  eurosym
                  fancyvrb
                  float
                  fontspec
                  geometry
                  grffile
                  hyperref
                  iftex
                  infwarerr
                  jknapltx
                  kvoptions
                  kvsetkeys
                  ltxcmds
                  parskip
                  pdfcol
                  pgf
                  rsfs
                  soul
                  tcolorbox
                  titling
                  trimspaces
                  ucs
                  ulem
                  unicode-math
                  upquote
                ]
              ))
            ];
            shellHook = ''
              export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
            '';
          };

          default = seguro-platform;
        };
      }
    )
    // {
      inherit overlays;
    };
}
