# SPDX-FileCopyrightText: 2023-2026 Steffen Vogel, OPAL-RT Germany GmbH
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
      inherit (nixpkgs) lib;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlayPyproject = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      overlayPyprojectEditable = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      defaultOverlay =
        final: prev:
        let
          python = final.python313;

          overlayAddMissingBuildInputs =
            pythonFinal: pythonPrev:
            let
              addSetuptools =
                pkg:
                pkg.overrideAttrs (old: {
                  nativeBuildInputs = old.nativeBuildInputs ++ pythonFinal.resolveBuildSystem { setuptools = [ ]; };
                });
            in
            {
              linuxfd = addSetuptools pythonPrev.linuxfd;
              villas-node = addSetuptools pythonPrev.villas-node;
              aws-logging-handlers = addSetuptools pythonPrev.aws-logging-handlers;
              odfpy = addSetuptools pythonPrev.odfpy;
              pygraphviz = pythonPrev.pygraphviz.overrideAttrs (old: {
                nativeBuildInputs = old.nativeBuildInputs ++ pythonFinal.resolveBuildSystem { setuptools = [ ]; };
                buildInputs = (old.buildInputs or [ ]) ++ [ final.graphviz ];
              });
            };

          pythonSet =
            (final.callPackage pyproject-nix.build.packages {
              inherit python;
            }).overrideScope
              (
                lib.composeManyExtensions [
                  pyproject-build-systems.overlays.wheel
                  overlayPyproject
                  overlayAddMissingBuildInputs
                ]
              );

          pythonSetEditable = pythonSet.overrideScope overlayPyprojectEditable;
        in
        {
          seguro-platform = pythonSet.mkVirtualEnv "seguro-platform-env" workspace.deps.default;
          seguro-platform-editable = pythonSetEditable.mkVirtualEnv "seguro-platform-dev-env" workspace.deps.all;

          uv = uv2nix.packages.${final.system}.uv-bin;
        };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            defaultOverlay
          ];
        };
      in
      {
        packages = {
          default = self.packages.${system}.seguro-platform;

          inherit (pkgs)
            seguro-platform
            seguro-platform-editable
            ;
        };

        devShells = {
          default = self.devShells.${system}.seguro-platform;

          seguro-platform = pkgs.mkShell {
            packages = with pkgs; [
              uv
              mosquitto
              graphviz

              seguro-platform-editable

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
              UV_PYTHON = pkgs.python313.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };

            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };
        };
      }
    )
    // {
      overlays = {
        default = defaultOverlay;
      };
    };
}
