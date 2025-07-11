# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Extreme EXOS."""

from .base import Extreme


class ExtremeExos(Extreme):
    """Implementation of Extreme EXOS Switch."""

    def __init__(self, *args, **kwargs):
        """Initialize base switch."""
        super(ExtremeExos, self).__init__(*args, **kwargs)
        self._connection.send_command("configure cli columns 256")
        self._connection.send_command("disable idletimeout")
