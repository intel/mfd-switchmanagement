# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ssh connection."""

import typing
from typing import List, Optional, Union

from netmiko import Netmiko, SSHDetect
from paramiko import SSHException
import logging

from .base import BaseSwitchConnection
from ..exceptions import SwitchException, SwitchConnectionException
from mfd_common_libs import add_logging_level, log_levels

logger = logging.getLogger(__name__)
logging.getLogger("netmiko").setLevel(logging.DEBUG)
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)
add_logging_level("CMD", log_levels.CMD)
add_logging_level("OUT", log_levels.OUT)


if typing.TYPE_CHECKING:
    from pathlib import Path


class SSHSwitchConnection(BaseSwitchConnection):
    """Implementation of SSH Connection."""

    def __init__(self, *args, **kwargs):
        """Init for ssh connection via Netimko."""
        super().__init__(*args, **kwargs)
        self._use_ssh_key: bool = kwargs.get("use_ssh_key", False)
        self._ssh_key_file: Union[str, "Path"] = kwargs.get("ssh_key_file", "")
        self._connection = self.connect()

    def connect(self) -> Netmiko:
        """
        Connect via Netmiko.

        Setup connection details, guest netmiko switch class and establish connection.

        :raises SwitchException on connection failure
        """
        if not self._secret:
            self._secret = self._password
        switch = {
            "host": f"{self._ip}",
            "username": self._username if self._username else "",
            "password": self._password if self._password else None,
            "secret": self._secret if self._secret else "",
            "key_file": str(self._ssh_key_file) if self._ssh_key_file else None,
            "use_keys": self._use_ssh_key,
            "device_type": self._device_type if self._device_type else "autodetect",
            "auth_timeout": self._auth_timeout,
        }
        # creating probably similar Netmiko class of switch
        try:
            delay = self._global_delay_factor if self._global_delay_factor is not None else self._NETMIKO_INIT_DELAY
            if switch["device_type"] == "autodetect":
                guesser = SSHDetect(**switch, global_delay_factor=delay)
                best_match = guesser.autodetect()
                switch["device_type"] = best_match
                if not best_match:
                    raise SwitchException("Detected not supported OS Switch, contact with developers of module")
                else:
                    logger.log(level=log_levels.MODULE_DEBUG, msg=f'Detected "{best_match}" switch type.')
            # to properly identify prompt on slower switches we're temporally increasing delay
            connection = Netmiko(**switch, global_delay_factor=delay)
            # if user did not provide delay, let's restore Netmiko default after setup
            if self._global_delay_factor is None:
                connection.global_delay_factor = 1
            connection.enable()
        except SSHException as e:
            raise SwitchException("Failure on connection") from e
        return connection

    def _reconnect(self) -> None:
        """
        Reconnect to switch.

        Reconnect and check connection status, if connection can not established return exception.

        :raises SwitchConnectionException on reconnection failure
        """
        self._connection._open()
        self._connection.enable()
        if not self._check_connection():
            raise SwitchConnectionException("Connection cannot be established!")

    def _check_connection(self) -> Optional[bool]:
        """Check connection to switch."""
        connection_status = (
            self._connection.remote_conn.transport.is_alive()
        )  # check if transport layer of channel of connection is active
        if connection_status:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Connection established.")
            return connection_status
        logger.log(level=log_levels.MODULE_DEBUG, msg="Connection not established.")

    @property
    def _remote(self) -> Netmiko:
        """If connection is dropped reconnect."""
        logging.getLogger("netmiko").setLevel(logging.CRITICAL)
        if not self._check_connection():
            self._reconnect()
        logging.getLogger("netmiko").setLevel(logging.DEBUG)
        return self._connection

    def send_command(self, command: str) -> str:
        """
        Send command via connection.

        :param command: command for send
        :return: Output from command
        """
        logger.log(level=log_levels.CMD, msg=f"Executing '{command}'")
        output = self._remote.send_command(command)
        logger.log(level=log_levels.OUT, msg=output)
        return output

    def send_command_expect(self, command: str, prompt: str) -> str:
        """
        Send command with expected prompt via connection.

        :param command: command for send
        :param prompt: expected string
        :return: Output from command
        """
        logger.log(level=log_levels.CMD, msg=f"Executing '{command}'    expect_string: {prompt}")
        output = self._remote.send_command(command, expect_string=prompt)
        logger.log(level=log_levels.OUT, msg=output)
        return output

    def exit_port_configuration(self) -> None:
        """Exit config mode."""
        self._remote.exit_config_mode()

    def send_command_list(self, commands: str) -> str:
        """
        Send commands list via connection.

        :param commands: commands for send
        :return: Output from commands
        """
        logger.log(level=log_levels.CMD, msg=f"Executing command list: '{commands}'")
        output = self._remote.send_config_set(commands, exit_config_mode=False, enter_config_mode=False)
        logger.log(level=log_levels.OUT, msg=output)
        return output

    def send_configuration(self, commands: List[str]) -> str:
        """
        Send commands list via connection as configuration.

        Enter configuration mode, send commands, exit configuration mode

        :param commands: commands for send
        :return: Output from commands
        """
        logger.log(level=log_levels.CMD, msg=f"Executing configuration: '{commands}'")
        output = self._remote.send_config_set(commands, exit_config_mode=True, enter_config_mode=True)
        logger.log(level=log_levels.OUT, msg=output)
        return output

    def disconnect(self) -> None:
        """Close connection with switch."""
        self._remote.disconnect()
