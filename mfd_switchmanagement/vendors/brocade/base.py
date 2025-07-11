# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Brocade base."""

import binascii
import re
import socket

from ...base import Switch


class Fabos(Switch):
    """Class for Brocade Fabos."""

    def __init__(self):
        """Init of Fabos."""
        super(Fabos, self).__init__()
        self.ipv6_regex = re.compile(r"0x[a-f0-9]{32}")

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command_list(["version | grep Fabric", "switchshow | grep switchType"])

    def change_standard_to_switch_IPv6_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv4 standard format
        """
        # Chassis ID: 0xfe80000000000000021b21fffe699eb9
        packed = socket.inet_pton(socket.AF_INET6, address)
        return "0x" + binascii.hexlify(packed)

    def change_switch_to_standard_ipv6_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv6 standard format
        """
        # Chassis ID: 0xfe80000000000000021b21fffe699eb9
        # remove leading 0x
        packed = binascii.unhexlify(address[2:])
        # convert to standard form fe80::21b:21ff....
        return socket.inet_ntop(socket.AF_INET6, packed)
