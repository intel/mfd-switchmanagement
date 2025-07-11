# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Cisco OS 6500."""

from .base import Cisco


class CiscoOS6500(Cisco):
    """Base class for Cisco 6500 type switch."""

    MAXIMUM_FRAME_SIZE = 9216
