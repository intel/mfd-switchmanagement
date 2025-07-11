# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for module exceptions."""


class SwitchConnectionException(Exception):
    """Exception for connection with switches."""


class SwitchException(Exception):
    """Exceptions for switch management."""


class SwitchWaitForLinkUpTimeout(SwitchException):
    """Exception for switch port link up timeout."""


class SwitchWaitForHoldingLinkStateTimeout(SwitchException):
    """Exception for switch port link state (up or down) timeout."""
