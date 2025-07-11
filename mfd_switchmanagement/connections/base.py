# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for base switch connection."""

from abc import ABC, abstractmethod
from ipaddress import ip_address
from typing import Union, Optional


class BaseSwitchConnection(ABC):
    """Base connection with switches."""

    _NETMIKO_INIT_DELAY = 2

    def __init__(
        self,
        ip: str = None,
        username: str = None,
        password: Optional[str] = None,
        secret: Optional[str] = None,
        auth_timeout: Union[int, float] = 30,
        device_type: Optional[str] = None,
        global_delay_factor: Optional[int] = None,
        *args,
        **kwargs,
    ):
        """
        Init connection with switch.

        :param ip: IP address of switch
        :param username: username for access
        :param password: password for access
        :param secret: secret password for access
        :param auth_timeout: Timeout in seconds for authentication
        :param device_type: device type from Netmiko SSH_MAPPER_BASE
        :param global_delay_factor: Multiplication factor affecting Netmiko delays (Netmiko default: 1)
                                    If not set, 2 will be set for connection creation time and 1 after it
        """
        self._ip = ip_address(ip)
        self._username = username
        self._password = password
        self._secret = secret
        self._auth_timeout = auth_timeout
        self._device_type = device_type
        self._connection = None
        self._global_delay_factor = global_delay_factor

    @abstractmethod
    def connect(self) -> object:
        """
        Establish connection with switch.

        :return: Connection object
        """
        raise NotImplementedError("Connecting method is not implemented")

    @abstractmethod
    def send_command(self, command: str) -> str:
        """
        Passthrough for sending command via connection.

        :param command: command for send
        :return: Output from command
        """
        raise NotImplementedError("Send command is not implemented")

    @abstractmethod
    def send_command_expect(self, command: str, prompt: str) -> str:
        """
        Passthrough for sending command via connection.

        :param command: command for send
        :param prompt: expected string
        :return: Output from command
        """
        raise NotImplementedError("Send command expect is not implemented")

    @abstractmethod
    def send_command_list(self, commands: str) -> str:
        """
        Passthrough for sending commands list via connection.

        :param commands: commands for send
        :return: Output from commands
        """
        raise NotImplementedError("Send command list is not implemented")

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection with switch."""
        raise NotImplementedError("Disconnect is not implemented")
