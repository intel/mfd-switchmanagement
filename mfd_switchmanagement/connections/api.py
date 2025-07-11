# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for API Connection."""

import logging
from abc import ABC, abstractmethod

from .base import BaseSwitchConnection
from mfd_common_libs import add_logging_level, log_levels

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class APISwitchConnection(BaseSwitchConnection, ABC):
    """Implementation of abstract API Connection."""

    def __init__(self, *args, **kwargs) -> None:
        """Init of API Connection."""
        super().__init__(*args, **kwargs)
        self._url = None
        self._http_header = None

    def connect(self) -> None:
        """Connect to required for API."""
        logger.log(level=log_levels.MODULE_DEBUG, msg="Connecting via API is not required")
        pass

    @abstractmethod
    def send_command(self, command: str) -> str:
        """
        Send command to switch via connection.

        :param command: command for send
        :return: Output from command
        """
        raise NotImplementedError("Send command for API is not implemented")

    def send_command_expect(self, command: str, prompt: str) -> str:
        """
        Passthrough for sending command via connection.

        :param command: command for send
        :param prompt: expected string
        :return: Output from command
        """
        raise NotImplementedError("Send command expect for API is not implemented")

    def disconnect(self) -> None:
        """Close connection with switch."""
        logger.log(level=log_levels.MODULE_DEBUG, msg="Disconnecting via API is not required")
        pass
