# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dell 8132."""

from .base import DellOS9


class DellOS9_8132(DellOS9):
    """Implementation for Dell 8132 switch."""

    def change_vlan(self, port: str, vlan: int) -> str:
        """
        Change Vlan port and switches mode to access.

        :param port: port of switch
        :param vlan: vlan to set
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            [
                "switchport mode access",
                "spanning-tree disable",
                "switchport trunk allowed vlan remove 1-4093",
                f"switchport access vlan {vlan}",
                "no sh",
            ]
        )
