# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0
{
  description = "Application packaged using uv2nix";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    let
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            (final: prev: {
              uv = uv2nix.packages.${system}.uv-bin;
            })
          ];
        };

        inherit (pkgs) lib;

        python = pkgs.python311;

        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
          }).overrideScope
            (
              lib.composeManyExtensions [
                pyproject-build-systems.overlays.wheel
                overlay
                (
                  final: prev:
                  let
                    addSetuptools =
                      pkg:
                      pkg.overrideAttrs (old: {
                        nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; };
                      });
                  in
                  {
                    linuxfd = addSetuptools prev.linuxfd;
                    villas-node = addSetuptools prev.villas-node;
                    aws-logging-handlers = addSetuptools prev.aws-logging-handlers;
                    odfpy = addSetuptools prev.odfpy;
                    pygraphviz = prev.pygraphviz.overrideAttrs (old: {
                      nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; };
                      buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.graphviz ];
                    });
                  }
                )
              ]
            );

        editableOverlay = workspace.mkEditablePyprojectOverlay {
          root = "$REPO_ROOT";
        };

        editablePythonSet = pythonSet.overrideScope editableOverlay;

        devEnv = editablePythonSet.mkVirtualEnv "seguro-platform-dev-env" workspace.deps.all;
      in
      {
        packages = rec {
          seguro-platform = pythonSet.mkVirtualEnv "seguro-platform-env" workspace.deps.default;
          default = seguro-platform;
        };

        devShells = rec {
          seguro-platform = pkgs.mkShell {
            packages = with pkgs; [
              uv
              devEnv
              mosquitto
              graphviz

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

            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = editablePythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };

            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };

          default = seguro-platform;
        };
      }
    );
}
