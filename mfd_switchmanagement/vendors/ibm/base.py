# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IBM base."""

import re
from ...base import Switch
from ...exceptions import SwitchException


class IBM(Switch):
    """
    Base class for IBM type switch.

    based on G8316 Rackswitch
    """

    # Ports examples: port 1-5,19,20,4090-4094 (access a mix of lists and ranges)
    PORT_REGEX = re.compile(r"^(port|portchannel) +(\d+)(((-|,)\d+))*$", re.I)

    def change_standard_to_switch_mac_address(self, address: str) -> str:
        """
        Convert standard mac address to switch mac address format.

        :param address: any mac address (no separators, separated using -:., lowercase, uppercase etc.
        :return: MAC address in switch accepted format (AA:BB:CC:DD:EE:FF)
        """
        a = r"([a-f0-9]{2})"
        double_regex = re.compile(rf"{a}{a}{a}{a}{a}{a}")
        hex_bytes = address.lower().replace(":", "").replace(".", "").replace("-", "")
        return ":".join(double_regex.match(hex_bytes).groups())

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            output = self._connection.send_command(f"sh mac-address-table address {mac.upper()}")
            port = re.search(r"([0-9A-F]{2}[:-]){5}[0-9A-F]{2}\s+(\d+)\s+\d+", output, re.I | re.M)
            if port:
                vlan = port.group(2)
                self._connection.send_command(f"no mac-address-table {mac.upper()} {vlan}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

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
            port = re.search(r"([0-9A-F]{2}[:-]){5}[0-9A-F]{2}\s+\d+\s+(\d+)", output, re.I | re.M)
            if port:
                return f"port {port.group(2)}"
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
            output = self._connection.send_command(f"sh mac-address-table address {mac.upper()}")
            """
            IBM_G8316-2A>show mac-address-table
            Mac address Aging Time: 300

            Total number of FDB entries : 24
                 MAC address       VLAN     Port    Trnk  State  Permanent
              -----------------  --------  -------  ----  -----  ---------
              00:aa:bb:cc:dd:ae       1    15              FWD
              00:aa:bb:cc:dd:af       1    16              FWD
              00:aa:bb:cc:dd:dc       1    19              FWD
            """
            vlan = re.search(r":\w{2}\s+(\d+)", output, re.I | re.M)
            if vlan:
                return int(vlan.group(1))
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def configure_vlan(self, ports: str, vlan: int, vlan_type: str, mode: str) -> None:
        """
        Configure vlan.

        Set trunking and tagging mode, create vlan if required, enable port

        :param ports: ports to configure
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports, mode, vlan, vlan_type)

        command_list = ["configure terminal"]
        if vlan:
            command_list.append(f"vlan {vlan:d}")
            command_list.append("exit")
        command_list.append(f"interface {ports}")
        command_list.append("switchport")

        if mode.lower().strip() == "access":
            command_list.append(f"switchport access vlan {vlan:d}")
            command_list.append("switchport mode access")
            command_list.append("spanning-tree portfast")
        elif mode.lower().strip() == "trunk":
            if not vlan:
                command_list.append("switchport trunk allowed vlan all")
            else:
                command_list.append(f"switchport trunk allowed vlan add {vlan:d}")
            if vlan_type.lower().strip() == "untagged":
                command_list.append(f"switchport trunk native vlan {vlan:d}")
            command_list.append("switchport mode trunk")
            command_list.append("spanning-tree portfast")
        command_list.append("no shutdown")
        self._connection.send_command_list(command_list)

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)

        self._connection.send_command_list(
            ["configure terminal", f"interface {ports}", "no switchport", "switchport", "no shutdown"]
        )
