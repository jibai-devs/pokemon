{
  description = "Pokemon project - Python 3.14 managed by uv";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, treefmt-nix, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        treefmtEval = treefmt-nix.lib.mkTreefmtEval {
          projectRootFile = ./flake.nix;
          imports = [ ./treefmt.nix ];
        };
      in
      {
        formatter = treefmtEval.config.build.wrapper;

        checks.formatting = treefmtEval.config.build.check self;

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # uv manages Python 3.14 — no python from nixpkgs
            uv

            # linting & formatting (nix-side)
            nixfmt-rfc-style
            statix
            deadnix

            # general dev tools
            git
            just
            jq
            fzf
            direnv

            # data tooling
            duckdb
            sqlite

            # CA certs for SSL
            cacert
          ];

          shellHook = ''
            export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export NIX_SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export REQUESTS_CA_BUNDLE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export CURL_CA_BUNDLE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"

            # uv manages Python — install 3.14 if missing
            uv python install 3.14 2>/dev/null || true

            # create venv if not present
            if [ ! -d .venv ]; then
              echo "Creating .venv with Python 3.14 via uv..."
              uv venv .venv --python 3.14
            fi
            export VIRTUAL_ENV="$(pwd)/.venv"
            export PATH="$VIRTUAL_ENV/bin:$PATH"

            echo "Python: $(python --version 2>&1)"
            echo "uv:     $(uv --version)"
          '';
        };
      }
    );
}
