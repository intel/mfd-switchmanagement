# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dell base."""

import re
import socket
import struct

from mfd_switchmanagement.base import Switch
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.utils.match import any_match


class DellOS9(Switch):
    """Handling Dell switch commands."""

    PORT_REGEX = re.compile(
        r"(^((gi|te|fo|tw|tf|fi|hu) ?(\d+/){1,2}\d+)(-(\d+/)*\d+)?( ?, ?"
        r"((gi|te|fo|tw|tf|fi|hu) ?(\d+/){1,2}\d+)(-(\d+/)*\d+)?)*$|^po\d+$)",
        re.I,
    )
    DEFAULT_INTERFACE_NAME = "ethernet "
    MINIMUM_FRAME_SIZE = 1518
    MAXIMUM_FRAME_SIZE = 9216

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Dell_os9 Switch."""
        return self.MAXIMUM_FRAME_SIZE

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command("show switch")

    def change_standard_to_switch_IPv6_address(self, address: str) -> str:
        """
        Convert standard IP address to switch IP address format.

        :param address: any mac address
        :return: mac address in IPv6 switch format
        """
        # Chassis id: 2, 254.128.00.00.00.00.00.00.
        packed = socket.inet_pton(socket.AF_INET6, address)
        return ".".join(f"{b:02}" for b in struct.unpack("16B", packed))

    def change_switch_to_standard_IPv6_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv6 standard format
        """
        # Chassis id: 2, 254.128.00.00.00.00.00.00.
        octets = [int(o) for o in address.split(".")]
        packed = struct.pack("16B", *octets)
        return socket.inet_ntop(socket.AF_INET6, packed)

    def _prepare_port_configuration(self, port: str) -> None:
        """
        Prepare port to configuration.

        :param port: port to configure
        """
        port_name = f"interface range {port}"
        self._connection.send_command_list(["conf", port_name])

    def disable_port(self, port: str, count: int = 1) -> None:
        """
        Disable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["shutdown", "end"])

    def enable_port(self, port: str, count: int = 1) -> None:
        """
        Enable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["no shutdown", "end"])

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        self._connection.send_command("no mtu")

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Enable jumbo frame.

        :param frame_size: Size of frame
        :param port: port of switch
        :raises ValueError if parameters are invalid
        """
        if frame_size < self.MINIMUM_FRAME_SIZE or frame_size > self.MAXIMUM_FRAME_SIZE:
            raise ValueError(
                f"Invalid frame size.  Valid values are '{self.MINIMUM_FRAME_SIZE}' " f"to '{self.MAXIMUM_FRAME_SIZE}'"
            )

        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        self._connection.send_command(f"mtu {frame_size}")

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

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError: if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)

        self._prepare_port_configuration(ports)
        self._connection.send_command_list(
            [
                "no shutdown",
                "no channel-group",
                "no switchport mode",
                "no switchport access vlan",
                "switchport general allowed vlan remove 2-4093",
                "no switchport general pvid",
                f"mtu {self.MAXIMUM_FRAME_SIZE}",
            ]
        )

    def get_port_by_mac(self, mac: str) -> str:
        """
        Get port of switch with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: port name
        :raises SwitchException: if port not found
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            output = self._connection.send_command(f"show mac-address-table address {mac}")
            # Example output from show mac-address-table command:
            #
            # GK6031-DR12-S6000-19505#show mac-address-table address 68:05:ca:c1:c8:ea
            # Codes: *N - VLT Peer Synced MAC
            # *I - Internal MAC Address used for Inter Process Communication
            # VlanId     Mac Address           Type          Interface        State
            #  1      aa:bb:cc:dd:ee:ff       Dynamic         Te 0/32         Active
            pattern = r"\s+\d+\s+(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\s+\w+\s+(?P<port>\S+\s+\S+)\s+\w+"
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                return match.group("port")  # return the port name
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
            Z9000-5D#show mac-address-table

            Codes: *N - VLT Peer Synced MAC
            VlanId     Mac Address           Type          Interface        State
             1      00:aa:bb:cc:e8:5c       Dynamic         Te 0/66         Active
             1      00:aa:bb:cc:e8:5d       Dynamic         Te 0/67         Active
             1      00:aa:bb:cc:91:58       Dynamic         Te 0/26         Active
             1      00:aa:bb:cc:91:59       Dynamic         Te 0/27         Active
             1      00:aa:bb:cc:a3:5a       Dynamic         Te 0/34         Active
            """
            vlan = any_match(output, r"\s+(\d+)\s+\w{2}:", flags=re.I)
            if vlan:
                return int(vlan[0])
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def enable_spanning_tree(self, port: str) -> str:
        """
        Enable spanning tree on given port.

        :param port: port of switch
        :return: Output from enabling
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(["no spanning-tree disable", "no spanning-tree portfast"])

    def disable_spanning_tree(self, port: str) -> str:
        """
        Disable spanning tree on given port.

        :param port: port of switch
        :return: Output from disabling
        """
        self._prepare_port_configuration(port)
        return self._connection.send_command_list(["spanning-tree disable", "spanning-tree portfast"])

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
                f"switchport access vlan {vlan}",
                "no sh",
            ]
        )

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        return self._connection.send_command(f"show running-config interface {port}")

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
                "switchport",
                "no switchport access vlan",
                "switchport mode trunk",
                "switchport trunk encapsulation dot1q",
                "switchport trunk allowed vlan remove 1-4093",
                f"switchport trunk allowed vlan add  {vlan}",
                "no sh",
            ]
        )

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        if "g" in port.lower():
            comm = f"show int status ethernet {port}"  # old Dell switches, require "ethernet" before port name
        else:
            comm = f"show int status {port}"  # new Dell switches
        output = self._connection.send_command(comm)
        if "Down" in output:
            return False
        elif "Up" in output:
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")

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
        if vlan == 1:  # Unable to set ports to tagged or untagged when they're already in VLAN 1 on Force10
            return None
        self._validate_configure_parameters(ports, mode, vlan, vlan_type)
        prange = ""
        if "-" in ports or "," in ports:
            prange = "range "

        self._connection.send_command_list(
            ["configure", f"interface  {prange}{ports}", "no shutdown", "switchport", "exit"]
        )
        ports = ports.replace(" ", "")
        self._connection.send_command(f"interface vlan {vlan}")
        if mode.lower().strip() == "access" or (
            (mode.lower().strip() == "trunk") and (vlan_type.lower().strip() == "untagged")
        ):
            self._connection.send_command(f"untagged {ports}")
        else:
            self._connection.send_command(f"tagged {ports}")
        self._connection.send_command("no shutdown")

    def get_port_speed(self, port: str) -> int:  # noqa W102
        output = self._connection.send_command_list(["end", f"show interfaces {port} status"])
        match = re.search(r"(?P<speed>\d+) Mbit", output, re.M)
        if match:
            return int(match.group("speed"))
        else:
            raise SwitchException(f"Couldn't retrieve port speed for port: {port} in output: {output}")

    def is_fec_enabled(self, port: str) -> bool:
        """
        Check in running config on given port whether FEC is enabled or not.

        :param port: port of switch
        :return: True if FEC is enabled, False otherwise.
        """
        out = self._connection.send_command(f"show running-config interface {port} | grep fec")
        match = re.search(r"(?P<fec>fec\s+enable)(?!no\s+fec\s+enable)", out)
        return bool(match)

    def enable_fec(self, port: str) -> bool:
        """
        Enable Set Forward Error correction on port.

        :param port: port of switch
        :return True if FEC was enabled, False otherwise.
        :raises SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["fec enable", "end"])
        return self.is_fec_enabled(port)

    def disable_fec(self, port: str) -> bool:
        """
        Enable Set Forward Error correction on port.

        :param port: port of switch
        :return True if FEC was disabled, False otherwise.
        :raises SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["no fec enable", "end"])
        return not self.is_fec_enabled(port)

    def set_default_fec(self, port: str) -> None:
        """
        Enable Set Forward Error correction on port.

        :param port: port of switch
        :raises SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["fec default", "end"])
