# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dell 7000."""

import re

from .base import DellOS9
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.utils.match import any_match


class DellOS9_7000(DellOS9):
    """Base class for Dell 7000 series type switch."""

    # Ports examples: gi1/0/1-2,ti1/1/10 |  po1
    PORT_REGEX = re.compile(r"(^((gi|te|fo)(\d+/){2}\d+)(-\d+)?(,((gi|te|fo)(\d+/){2}\d+)(-\d+)?)*$|^po\d+$)", re.I)
    DEFAULT_INTERFACE_NAME = ""

    def get_port_by_mac(self, mac: str) -> str:
        """
        Get port with the specified MAC address.

        :param mac: mac address to find port
        :return: port name
        :raises SwitchException: if port not found
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            output = self._connection.send_command(f"sh mac-address-table address {mac.upper()}")
            port = any_match(output, r"((gi|te|fo)(\d+/){2}\d+)", flags=re.I)
            if port:
                return port[0][0]
            else:
                raise SwitchException(f"Could not find port for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def get_vlan_by_mac(self, mac: str) -> int:
        """
        Get VLAN of port with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: VLAN ID
        :raises SwitchException: if VLAN not found
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            """
                    show mac address-table address 90E2.BA14.AA3F

                    Aging time is 300 Sec

                    Vlan     Mac Address           Type        Port
                    -------- --------------------- ----------- ---------------------
                    301      90AA.BBCC.DD3F        Dynamic     Gi1/0/25


                    """
            output = self._connection.send_command(f"sh mac-address-table address {mac.upper()}")
            vlan = any_match(output, r"(\d+)\s+\w{4}\.", flags=re.I)
            if vlan:
                return int(vlan[0])
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")
