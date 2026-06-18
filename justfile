default := "list"

list:
    @just --list

run *args:
    uv run python -m pokemon {{ args }}

test *args:
    uv run pytest {{ args }}

lint:
    uv run ruff check .

fmt:
    uv run ruff format .
    nix fmt

typecheck:
    uv run pyright

check: fmt lint typecheck test

clean:
    rm -rf .venv __pycache__ .ruff_cache .pytest_cache dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

sync:
    uv sync

data *args:
    duckdb data/ {{ args }}
