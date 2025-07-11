# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Data structures."""

from enum import Enum


class State(Enum):
    """States."""

    ENABLE = "enable"
    DISABLE = "disable"


class ETSMode(Enum):
    """ETS Modes."""

    WRR = "wrr"
    STRICT = "strict"
