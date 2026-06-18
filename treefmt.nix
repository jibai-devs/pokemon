{ pkgs, ... }:
{
  projectRootFile = "flake.nix";

  programs.nixfmt.enable = true;
  programs.deadnix.enable = true;
  programs.statix.enable = true;

  # ruff handles Python formatting + linting
  programs.ruff.enable = true;
  programs.ruff.settings = {
    fix = true;
    eager = true;
  };

  settings.global.excludes = [
    ".venv/*"
    "data/*"
    "*.lock"
  ];
}
