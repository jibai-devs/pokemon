"""ctypes binding for the engine native search API (plan 009 Phase 2).

Exposes ``SearchBegin`` / ``SearchStep`` / ``SearchEnd`` / ``SearchRelease``
against ``libcg.so`` so Python can fork the live game state and roll decisions
forward under a full rules engine.

``observation`` on success matches live ``obs`` shape (``select`` / ``current`` /
``logs``), so existing ``Ctx`` helpers parse search nodes without changes.
"""

from __future__ import annotations

import ctypes
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokemon.types import Observation, SearchStartConfig

_LIB: ctypes.CDLL | None = None
_INITIALIZED = False


def _candidate_lib_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("POKEMON_LIBCG")
    if env:
        paths.append(Path(env))
    here = Path(__file__).resolve()
    paths.append(here.parents[2] / "reverse-engineering" / "data" / "sample_submission" / "cg" / "libcg.so")
    try:
        import kaggle_environments.envs.cabt.cg as cabt_cg

        paths.append(Path(cabt_cg.__file__).resolve().parent / "libcg.so")
        paths.append(Path(cabt_cg.__file__).resolve().parent / "cg.dll")
    except Exception:
        pass
    return paths


def _load_lib() -> ctypes.CDLL:
    global _LIB, _INITIALIZED
    if _LIB is not None:
        return _LIB

    # Prefer the already-loaded kaggle sim module so GameInitialize is shared.
    try:
        from kaggle_environments.envs.cabt.cg.sim import lib as shared

        _LIB = shared
        _INITIALIZED = True
        _configure_search_symbols(_LIB)
        return _LIB
    except Exception:
        pass

    last_err: Exception | None = None
    for path in _candidate_lib_paths():
        if not path.exists():
            continue
        try:
            lib = ctypes.cdll.LoadLibrary(str(path))
            if not _INITIALIZED:
                lib.GameInitialize()
                _INITIALIZED = True
            _configure_search_symbols(lib)
            _LIB = lib
            return lib
        except Exception as e:
            last_err = e
    raise RuntimeError(f"could not load libcg for native search: {last_err}")


def _configure_search_symbols(lib: ctypes.CDLL) -> None:
    lib.AgentStart.restype = ctypes.c_void_p
    lib.AgentStart.argtypes = []

    lib.SearchBegin.restype = ctypes.c_char_p
    lib.SearchBegin.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]

    lib.SearchStep.restype = ctypes.c_char_p
    lib.SearchStep.argtypes = [
        ctypes.c_void_p,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]

    lib.SearchEnd.argtypes = [ctypes.c_void_p]
    lib.SearchRelease.argtypes = [ctypes.c_void_p, ctypes.c_longlong]

    lib.BattleFinish.argtypes = [ctypes.c_void_p]


def _as_int_array(ids: list[int]) -> tuple[ctypes.Array[ctypes.c_int] | None, Any]:
    """Return (buffer, pointer). Empty lists → null pointer (CopyIdPtr count 0)."""
    if not ids:
        return None, None
    buf = (ctypes.c_int * len(ids))(*ids)
    return buf, buf


@dataclass
class SearchResult:
    error: int
    search_id: int | None
    observation: Observation | None
    raw: dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.error == 0 and self.observation is not None and self.search_id is not None


def _parse_result(raw_bytes: bytes | None) -> SearchResult:
    if not raw_bytes:
        return SearchResult(error=99, search_id=None, observation=None, raw={})
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        return SearchResult(error=99, search_id=None, observation=None, raw={})
    err = int(data.get("error", 99))
    state = data.get("state")
    if not state or err != 0:
        return SearchResult(error=err, search_id=None, observation=None, raw=data)
    return SearchResult(
        error=err,
        search_id=int(state["searchId"]),
        observation=state["observation"],
        raw=data,
    )


class SearchSession:
    """Owns one AgentStart handle; call close()/use as context manager."""

    def __init__(self) -> None:
        self._lib = _load_lib()
        self._handle = self._lib.AgentStart()
        if not self._handle:
            raise RuntimeError("AgentStart returned null")

    def close(self) -> None:
        if self._handle:
            self._lib.SearchEnd(self._handle)
            self._lib.BattleFinish(self._handle)
            self._handle = None

    def __enter__(self) -> SearchSession:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def begin(self, search_begin_input: str, config: SearchStartConfig) -> SearchResult:
        if not self._handle:
            raise RuntimeError("session closed")
        blob = search_begin_input.encode("ascii")
        reserves: list[Any] = []  # keep arrays alive through the call

        def ptr(ids: list[int]):
            buf, p = _as_int_array(ids)
            if buf is not None:
                reserves.append(buf)
            return p

        raw = self._lib.SearchBegin(
            self._handle,
            blob,
            len(blob),
            ptr(list(config.get("myDeck") or [])),
            ptr(list(config.get("myPrize") or [])),
            ptr(list(config.get("enemyDeck") or [])),
            ptr(list(config.get("enemyPrize") or [])),
            ptr(list(config.get("enemyHand") or [])),
            ptr(list(config.get("enemyActive") or [])),
            1 if config.get("manualCoin") else 0,
        )
        return _parse_result(raw)

    def step(self, search_id: int, selections: list[int]) -> SearchResult:
        if not self._handle:
            raise RuntimeError("session closed")
        if not selections:
            arr = (ctypes.c_int * 0)()
            raw = self._lib.SearchStep(self._handle, search_id, arr, 0)
        else:
            arr = (ctypes.c_int * len(selections))(*selections)
            raw = self._lib.SearchStep(self._handle, search_id, arr, len(selections))
        return _parse_result(raw)

    def release(self, search_id: int) -> None:
        if self._handle:
            self._lib.SearchRelease(self._handle, search_id)

    def end(self) -> None:
        if self._handle:
            self._lib.SearchEnd(self._handle)
