_: {
  projectRootFile = "flake.nix";

  programs.nixfmt.enable = true;
  programs.deadnix.enable = true;
  programs.statix.enable = true;

  # ruff handles Python linting (check --fix) + formatting
  programs.ruff-check.enable = true;
  programs.ruff-format.enable = true;

  settings.global.excludes = [
    ".venv/*"
    "data/*"
    "*.lock"
  ];
}
