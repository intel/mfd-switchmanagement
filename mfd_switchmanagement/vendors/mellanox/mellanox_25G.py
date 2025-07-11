# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Mellanox 25G."""

from .base import Mellanox
from ...base import FecMode
from ...exceptions import SwitchException


class Mellanox25G(Mellanox):
    """
    Implementation for 25G Mellanox switch.

    Adds few specific things when it comes 25G link config
    """

    def set_fec(self, port: str, fec_mode: FecMode) -> bool:
        """
        Set Forward Error correction on port.

        :param port: port of switch
        :param fec_mode: Value of FEC
        :raises SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["shutdown", f"fec-override {fec_mode.value}", "no shutdown"])
        return self._is_fec_mode_set(port, fec_mode)

    def get_fec(self, port: str) -> str:
        """
        Get Forward error correction on port.

        :param port: port of switch
        :return: FEC Mode
        """
        port_cfg = self.show_port_running_config(port)
        fec = [mode.value for cfg in port_cfg.split("\n") for mode in FecMode if mode.value in cfg]
        if fec:
            return fec[0]
        raise SwitchException(f"Error while checking FEC on port: {port}")

    def _is_fec_mode_set(self, port: str, fec_mode: FecMode) -> bool:
        return self.get_fec(port) == fec_mode.value
