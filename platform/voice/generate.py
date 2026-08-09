#!/usr/bin/env python3
"""Stable entry point for the current voice generator implementation."""

import importlib.util
from pathlib import Path


_IMPLEMENTATION = Path(__file__).with_name("generate_v2.py")
_SPEC = importlib.util.spec_from_file_location("open_city_voice_generator", _IMPLEMENTATION)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

parse_time_range = _MODULE.parse_time_range


def main():
    return _MODULE.main()


if __name__ == "__main__":
    main()
