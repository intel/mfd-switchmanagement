# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Arista7050."""

from .base import Arista


class Arista7050(Arista):
    """Class for Arista 7050 switch."""

    MINIMUM_FRAME_SIZE = 68
    MAXIMUM_FRAME_SIZE = 9214
