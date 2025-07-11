# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Cisco base."""

import logging
import re
import socket
import struct

from ...base import Switch
from ...exceptions import SwitchException
from ...utils.match import any_match

from mfd_common_libs import add_logging_level, log_levels

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class Cisco(Switch):
    """Handling Cisco switch commands."""

    MINIMUM_FRAME_SIZE = 1523
    MAXIMUM_FRAME_SIZE = 17800

    PORT_REGEX = re.compile(
        r"^(e|f|TenGigabitEthernet|GigabitEthernet|TwoGigabitEthernet|FiveGigabitEthernet"
        r"|TwentyFiveGigE|FortyGigabitEthernet|g(i)?|t(e)?|tw|fi|twe|fo|v)\d+/\d+([-/]\d+)"
        r"?(,(e|f|TenGigabitEthernet|GigabitEthernet|TwoGigabitEthernet|FiveGigabitEthernet"
        r"|TwentyFiveGigE|FortyGigabitEthernet|g(i)?|t(e)?|tw|fi|twe|fo|v)\d+/\d+([-/]\d+)?){0,4}$",
        re.I,
    )

    PORT_CHANNEL_REGEX = re.compile(r"^(?P<port_channel>port-channel\s\d+)$", re.I)

    QOS_PRIORITY = [0, 1, 2, 3, 4, 5, 6, 7]

    INCORRECT_COMMAND_OUTPUT = "% Invalid input detected at '^' marker."

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Cisco Switch."""
        return self.MAXIMUM_FRAME_SIZE

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command("sh ver")

    def change_switch_to_standard_ipv6_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv6 standard format
        """
        # Chassis id: 2, 254.128.00.00.00.00.00.00.
        octets = [int(o) for o in address.split(".")]
        packed = struct.pack("16B", *octets)
        return socket.inet_ntop(socket.AF_INET6, packed)

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
            output = self._connection.send_command(f"sh mac-address-table address {mac}")
            if self.INCORRECT_COMMAND_OUTPUT in output:
                output = self._connection.send_command(f"sh mac address-table address {mac}")
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"sw get_pbm: {output}")
            port = any_match(
                output,
                r"((?:e|f|gi|te|v|TenGigabitEthernet|GigabitEthernet)\d+/\d+/*\d*)",
                flags=re.I,
            )
            if port:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"found port {port[0]}")
                return port[0]
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
            output = self._connection.send_command(f"sh mac-address-table address {mac}")
            if self.INCORRECT_COMMAND_OUTPUT in output:
                output = self._connection.send_command(f"sh mac address-table address {mac}")

            """
            Cisco6509_5H>show mac-address-table
            Legend: * - primary entry
                    age - seconds since last seen
                    n/a - not available

              vlan   mac address     type    learn     age              ports
            ------+----------------+--------+-----+----------+--------------------------
            *  352  3333.0000.000d    static  Yes          -   Gi1/1,Gi1/2,Gi1/3,Gi1/4
            """
            """
            LKV-SW-9300#sh mac address-table address 0000.00c9.a000
                    Mac Address Table
            -------------------------------------------

            Vlan    Mac Address       Type        Ports
            ----    -----------       --------    -----
               1    0000.00c9.a000    DYNAMIC     Te1/0/9
            """
            vlan = any_match(output, r"(\d+)\s+\w{4}\.", flags=re.I)
            if vlan:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"found vlan {vlan[0]}")
                return int(vlan[0])
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=port)
        command_list = ["configure terminal"]
        if "all" in port:
            command_list.append("no system mtu jumbo")
        else:
            command_list.append(f"interface range {port}")
            command_list.append("no mtu")
        self._connection.send_command_list(command_list)

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Enable jumbo frame.

        :param frame_size: Size of frame
        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        if frame_size < self.MINIMUM_FRAME_SIZE or frame_size > self.MAXIMUM_FRAME_SIZE:
            raise ValueError(
                f"Invalid frame size {frame_size}. "
                f"Valid values are '{self.MINIMUM_FRAME_SIZE}' to '{self.MAXIMUM_FRAME_SIZE}'"
            )

        self._validate_port_and_port_channel_syntax(both_syntax=port)

        command_list = ["configure terminal"]
        if "all" in port:
            command_list.append(f"system mtu jumbo {frame_size}")
        else:
            command_list.append(f"interface range {port}")
            command_list.append(f"mtu {frame_size}")
        self._connection.send_command_list(command_list)

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            self._connection.send_command(f"clear mac address-table dynamic address {mac.upper()}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def default_ports(self, ports: str) -> str:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)
        command_list = [
            "configure terminal",
            f"default interface range {ports}",
            f"interface range {ports}",
            "switchport",
            "switchport trunk allowed vlan none",
            f"mtu {self.MAXIMUM_FRAME_SIZE}",
            "no shutdown",
        ]
        return self._connection.send_command_list(command_list)

    def show_vlans(self) -> str:
        """
        Show all ports vlan configuration.

        :return: Vlans information
        """
        return self._connection.send_command("show vlan")

    def show_ports_status(self) -> str:
        """
        Show all ports status.

        :return: Ports information
        """
        return self._connection.send_command("show int status")

    def enable_spanning_tree(self, port: str) -> str:
        """
        Enable spanning tree on given port.

        :param port: port of switch
        :return: Output from enabling
        """
        self._prepare_port_configuration(port)
        command_list = [
            "spanning-tree portfast disable",
            "spanning-tree bpdufilter disable",
        ]
        return self._connection.send_command_list(command_list)

    def disable_spanning_tree(self, port: str) -> str:
        """
        Disable spanning tree on given port.

        :param port: port of switch
        :return: Output from disabling
        """
        self._prepare_port_configuration(port)
        command_list = ["spanning-tree portfast", "spanning-tree bpdufilter enable"]
        return self._connection.send_command_list(command_list)

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        self._validate_configure_parameters(ports=port)

        if shutdown:
            self.disable_port(port, 1)
        else:
            self.enable_port(port, 1)

    def enable_port(self, port: str, count: int = 3) -> None:
        """
        Enable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._prepare_port_configuration(port)
        for _ in range(count):
            self._connection.send_command("no sh")

    def disable_port(self, port: str, count: int = 3) -> None:
        """
        Disable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._prepare_port_configuration(port)
        for _ in range(count):
            self._connection.send_command("sh")

    def change_vlan(self, port: str, vlan: int) -> str:
        """
        Change Vlan port and switches mode to access.

        :param port: port of switch
        :param vlan: vlan to set
        """
        self._prepare_port_configuration(port)
        command_list = [
            "switchport mode access",
            "no switchport trunk allowed vlan",
            f"switchport access vlan {vlan}",
            "no sh",
            "spanning-tree portfast",
        ]
        return self._connection.send_command_list(command_list)

    def set_trunking_interface(self, port: str, vlan: int) -> str:
        """
        Change mode to trunk on port and allows vlan traffic on this port.

        :param port: port of switch
        :param vlan: vlan to set
        :return: Output from setting
        """
        self._prepare_port_configuration(port)
        command_list = [
            "switchport",
            "no switchport access vlan",
            "switchport mode trunk",
            f"switchport trunk allowed vlan {vlan}",
            f"switchport trunk allowed vlan add {vlan}",
            "no sh",
        ]
        return self._connection.send_command_list(command_list)

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
        command_list.append(f"interface range {ports}")
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
            command_list.append("switchport trunk encapsulation dot1q")
            if vlan_type.lower().strip() == "untagged":
                command_list.append(f"switchport trunk native vlan {vlan:d}")
            command_list.append("switchport mode trunk")
            command_list.append("spanning-tree portfast trunk")
        command_list.append("no shutdown")
        self._connection.send_command_list(command_list)

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        return self._connection.send_command(f"show running-config interface {port}")

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        comm = f"show ip int brief {port}"
        output = self._connection.send_command(comm)
        if "down" in output:
            return False
        elif "up" in output:
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")

    def show_lldp_info(self, port: str) -> str:
        """
        Verify the LLDP neighbor info on switch.

        :param port: port of switch
        :return: Output of the command
        """
        return self._connection.send_command(f"show lldp neighbors interface {port} detail")

    def disable_cdp(self) -> str:
        """
        Disable CDP on Switch.

        :return: output of the command
        """
        return self._connection.send_configuration(["no cdp enable"])

    def configure_lldp(self, port: str, param: str) -> str:
        """
        Configure LLDP on switch.

        :param port: port of switch
        :param param: Parameter to receive or transmit
        :raises: ValueError if parameters are incorrect
        """
        if param:
            if param not in ["receive", "transmit"]:
                raise ValueError(f"Invalid parameter: {param}. Valid values are 'receive' or 'transmit'.")
            else:
                return self._connection.send_configuration(
                    [
                        f"interface {port}",
                        f"lldp {param}",
                    ]
                )
