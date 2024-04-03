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

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    poetry2nix,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      p2n = poetry2nix.lib.mkPoetry2Nix {inherit pkgs;};

      overrides = p2n.overrides.withDefaults (
        self: super: let
          # Workaround https://github.com/nix-community/poetry2nix/issues/568
          addBuildInputs = name: buildInputs:
            super.${name}.overridePythonAttrs (old: {
              buildInputs = (builtins.map (x: super.${x}) buildInputs) ++ (old.buildInputs or []);
            });
          mkOverrides = pkgs.lib.attrsets.mapAttrs (name: value: addBuildInputs name value);
        in
          mkOverrides {
            aws-logging-handlers = ["setuptools"];
            villas-python = ["setuptools"];
            types-python-slugify = ["setuptools"];
            paho-mqtt = ["hatchling"];
            pyxlsb = ["setuptools"];
            rfc3161ng = ["setuptools"];
          }
          // {
            python-calamine = super.python-calamine.override {
              preferWheel = true;
            };
            apprise = super.apprise.override {
              preferWheel = true;
            };
            pandas = super.pandas.override {
              preferWheel = true;
            };
            mypy = super.mypy.override {
              preferWheel = true;
            };
          }
      );
    in {
      packages = {
        seguro-platform = p2n.mkPoetryApplication {
          projectDir = ./.;
          groups = ["dev"];
          inherit overrides;
        };
        env = p2n.mkPoetryEnv {
          projectDir = ./.;
          groups = ["jupyter"];
          editablePackageSources = {
            seguro-platform = ./seguro;
          };
          inherit overrides;
        };
        default = self.packages.${system}.seguro-platform;
      };

      devShells.default = pkgs.mkShell {
        inputsFrom = [self.packages.${system}.seguro-platform];
        packages = with pkgs // self.packages.${system}; [
          mypy
          poetry
          env
          (p2n.mkPoetryScriptsPackage {
            projectDir = ./.;
          })

          # For notebook_executor
          # See: https://github.com/jupyter/nbconvert/issues/1328#issuecomment-1768665936
          (texliveSmall.withPackages
            (ps:
              with ps; [
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
              ]))
        ];
        shellHook = ''
          export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
        '';
      };
    });
}
