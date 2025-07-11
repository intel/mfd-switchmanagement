# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dell S4128."""

from .base import DellOS9
from mfd_switchmanagement.exceptions import SwitchException


class DellOS9_S4128(DellOS9):
    """Implementation for Dell S4128T-ON switch."""

    def _prepare_port_configuration(self, port: str) -> str:
        """
        Prepare port to configuration.

        :param port: port to configure
        """
        return self._connection.send_command_list(["configure terminal", f"interface range {port}"])

    def enable_spanning_tree(self, port: str) -> str:
        """
        Enable spanning tree on given port.

        :param port: port of switch
        :return: Output from enabling
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            ["no spanning-tree port type edge", "spanning-tree bpdufilter disable"]
        )

    def disable_spanning_tree(self, port: str) -> str:
        """
        Disable spanning tree on given port.

        :param port: port of switch
        :return: Output from disabling
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(["spanning-tree port type edge", "spanning-tree bpdufilter enable"])

    def change_vlan(self, port: str, vlan: int) -> str:
        """
        Change Vlan port and switches mode to access.

        :param port: port of switch
        :param vlan: vlan to set
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            ["switchport mode access", "spanning-tree disable", f"switchport access vlan {vlan}", "no shutdown"]
        )

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        return self._connection.send_command(f"show running-configuration interface {port}")

    def set_trunking_interface(self, port: str, vlan: int) -> str:
        """
        Change mode to trunk on port and allows vlan traffic on this port.

        :param port: port of switch
        :param vlan: vlan to set
        :return: Output from setting
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            [
                "no switchport",
                "no switchport access vlan",
                "switchport mode trunk",
                f"switchport trunk allowed vlan {vlan}",
                "no shutdown",
            ]
        )

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        output = self._connection.send_command(f"show interface {port}")
        if "down" in output:
            return False
        elif "up" in output:
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")
