# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Cisco OS 4000."""

from .base import Cisco


class CiscoOS4000(Cisco):
    """Base class for Cisco 4000 type switch."""

    MINIMUM_FRAME_SIZE = 1500
    MAXIMUM_FRAME_SIZE = 9198
