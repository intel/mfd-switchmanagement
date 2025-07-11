# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Junos base."""

import re
from time import sleep
from typing import List

from ...base import Switch
from ...utils.match import any_match
from ...exceptions import SwitchException


def decimal_to_bin(decimal_value: str) -> str:
    """
    Convert decimal value to binary number.

    :param decimal_value: decimal value
    :type decimal_value: str/unicode/int
    :return: binary value in 3 bit format e.g. 011.
    """
    return f"{int(decimal_value):03b}"


class Junos(Switch):
    """Implementation of Junos."""

    MINIMUM_FRAME_SIZE = 1514
    MAXIMUM_FRAME_SIZE = 9216
    PORT_REGEX = re.compile(r"^((?:et|xe)-\d+/\d+/\d+(?::\d+)?)$")
    MAXIMUM_SUPPORT_TRAFFIC_CLASSES = 3

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Junos Switch."""
        return self.MAXIMUM_FRAME_SIZE

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command("edit")
        if shutdown:
            self._connection.send_command(f"set interfaces {port} disable")
        else:
            self._connection.send_command(f"delete interfaces {port} disable")
        self._connection.send_command("commit")
        self._connection.send_command("exit")

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Enable jumbo frame.

        :param frame_size: Size of frame
        :param port: port of switch
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command_list(["edit", f"set interfaces {port} mtu {frame_size}", "commit", "exit"])

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command_list(["edit", f"delete interfaces {port} mtu", "commit", "exit"])

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)

        self._connection.send_command_list(
            [
                "edit",
                f"edit interfaces {ports}",
                "delete native-vlan-id",
                f"set mtu {self.MAXIMUM_FRAME_SIZE}",
                "delete disable",
                "delete unit 0 family ethernet-switching interface-mode",
                "delete unit 0 family ethernet-switching vlan members",
                "commit",
                "exit",
                "exit",
            ]
        )

    def get_port_by_mac(self, mac: str) -> str:
        """
        Get port with the specified MAC address.

        :param mac: mac address to find port
        :return: port name
        :raises SwitchException: if port not found
        :raises ValueError: if provided MAC address is incorrect
        """
        mac = mac.lower()
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid mac address: {mac}")

        output = self._connection.send_command("show ethernet-switching table brief | no-more")
        lines = output.split("\n")
        if len(lines) < 2:
            raise SwitchException(f"Could not find port for MAC address {mac}")
        for line in lines[1:]:
            if mac in line:
                return line.split()[4].split(".")[0]

        output = self._connection.send_command("show lldp neighbors | no-more")
        lines = output.split("\n")
        if len(lines) < 2:
            raise SwitchException(f"Could not find port for MAC address {mac}")
        for line in lines[1:]:
            if mac in line:
                return line.split()[0]
        raise SwitchException(f"Could not find port for MAC address {mac}")

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        :raises ValueError: if provided MAC address is incorrect
        """
        mac = mac.lower()
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid mac address: {mac}")

        self._connection.send_command(f"clear ethernet-switching table {mac}")
        port = self.get_port_by_mac(mac)
        self._connection.send_command(f"clear lldp neighbors interface {port}")

    def get_vlan_by_mac(self, mac: str) -> int:
        """
        Get VLAN of port with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: VLAN ID
        :raises SwitchException: if VLAN not found
        :raises ValueError: if provided MAC address is incorrect
        """
        mac = mac.lower()
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid mac address: {mac}")
        port = self.get_port_by_mac(mac)
        output = self._connection.send_command("show vlans | no-more")
        lines = output.split("\n")
        vlan_tag = 0
        for line in lines[1:]:
            if "Routing instance" in line:
                continue
            if len(line) > 1 and line[0] != " ":
                vlan_tag = line.split()[2]
                continue
            if port + "." in line:
                return int(vlan_tag)
        raise SwitchException("VLAN not found")

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
        self._validate_configure_parameters(ports=ports, vlan_type=vlan_type)

        output = self._connection.send_command("show vlans | no-more")
        lines = output.split("\n")
        for line in lines[1:]:
            if "Routing instance" in line:
                continue
            if len(line) > 1 and line[0] != " ":
                vlan_tag = line.split()[2]
                if int(vlan_tag) == int(vlan):
                    vlan_name = line.split()[1]

                    self._connection.send_command("edit")
                    self._connection.send_command("edit interfaces")
                    if vlan_type == "tagged":
                        self._connection.send_command(
                            f"set {ports} unit 0 family ethernet-switching interface-mode trunk"
                        )
                    self._connection.send_command(
                        f"set {ports} unit 0 family ethernet-switching vlan members {vlan_name}"
                    )
                    self._connection.send_command("commit")
                    self._connection.send_command("exit")
                    self._connection.send_command("exit")
                    return

    def get_max_supported_traffic_classes(self) -> int:
        """
        Get maximum number of traffic classes that switch supports.

        :return: maximum number of traffic classes, Juniper switch supports (3)
        """
        return self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES

    def get_port_dcbx_version(self, port: str) -> str:
        """
        Get dcbx version of port.

        :param port: port to check
        :return: dcbx version
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"show configuration protocols dcbx interface {port} dcbx-version")
        dcbx = any_match(output, r"dcbx-version (.{4})-", flags=re.I)
        if dcbx:
            return "ieee" if dcbx[0] == "ieee" else "cee"
        else:
            raise SwitchException(f"Error retrieving DCBX version for port {port}")

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set dcbx version of port.

        :param port: port to configure
        :param mode: version
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        dcbx_mode = mode if mode == "ieee" else "dcbx"

        self._connection.send_command_list(
            ["edit", "edit protocols dcbx", f"set interface {port} dcbx-version {dcbx_mode}", "commit", "exit", "exit"]
        )

    def get_port_dcb_map(self, port: str) -> str:
        """
        Get the DCB MAP name applied to a given switch port.

        :param port: switch port
        :return: DCB MAP name
        :raises SwitchException on failure
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"show configuration class-of-service interfaces {port}")
        dcbmap = any_match(output, r"ieee-802.1 (.+)-clsf", flags=re.I)
        if dcbmap:
            return dcbmap[0]
        else:
            raise SwitchException(f"Error retrieving DCB-MAP for port {port}")

    def set_port_dcb_map(self, port: str, dcbmap: str) -> None:
        """
        Set the DCB MAP for a switch port to a given name.

        :param port: port of switch
        :param dcbmap: DCB-MAP name
        :raises ValueError if parameters are invalid

        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command("edit")
        self._connection.send_command("edit class-of-service interfaces")
        self._connection.send_command(f"delete {port}")

        for tc in range(self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES):
            self._connection.send_command(
                f"set {port} forwarding-class-set tc{tc} " f"output-traffic-control-profile {dcbmap}-tc{tc}-tcp"
            )
            sleep(2)

        self._connection.send_command(f"set {port} congestion-notification-profile {dcbmap}-cnp")
        self._connection.send_command(f"set {port} unit 0 classifiers ieee-802.1 {dcbmap}-clsf")
        sleep(2)
        self._connection.send_command("commit")
        sleep(10)
        self._connection.send_command("exit")
        self._connection.send_command("exit")

    def set_dcb_map_up(self, dcbmap: str, up: str, tc: int = 0) -> None:
        """
        Set a User Priority Group on a DCB MAP.

        :param tc: Traffic class
        :param dcbmap: DCB-MAP name
        :param up: User Priority Group
        :raises ValueError if parameters are invalid
        """
        pattern = any_match(up, r"(([0-7]\s){1,7}|([0-7]))", flags=re.I)
        if not pattern:
            raise ValueError("Invalid priority-pgid format")

        if tc >= self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(
                f"Junos switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:d} " f"traffic classes and groups."
            )

        self._connection.send_command_list(
            ["edit", "edit class-of-service", "edit classifiers", f"delete ieee-802.1 {dcbmap}-clsf"]
        )

        bin_up = ""
        for item in up.split(" "):
            bin_up += f"{decimal_to_bin(item)} "

        for pg in range(tc + 1):
            self._connection.send_command(
                f"set ieee-802.1 {dcbmap}-clsf forwarding-class pg{pg:d} " f"loss-priority low code-points [ {bin_up}]"
            )
            sleep(2)

        self._connection.send_command_list(["commit", "exit", "exit", "exit"])

    def set_dcb_map_tc(self, dcbmap: str, tc: int, bw: int, pfc: str, up_for_pfc: List = None) -> None:
        """
        Configure a DCB MAP with TC, BW and PFC settings.

        :param up_for_pfc: User Priority for PFC
        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :param bw: Bandwidth %
        :param pfc: PFC state
        :raises ValueError if parameters are invalid
        """
        res = bw in range(100)
        if not bw or not res:
            raise ValueError("Invalid bandwidth value, must be in 0-100 range")

        if not pfc or pfc not in ("off", "on"):
            raise ValueError("Invalid pfc value, must be either 'on' or 'off'")

        if tc not in range(self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES):
            raise ValueError(f"Invalid TC value, must be between 0-{self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES - 1:d} range")

        if pfc == "on":
            for code_point in up_for_pfc if up_for_pfc else [3, 4]:
                self.set_congestion_notification_profile(dcbmap, str(code_point))

        self._connection.send_command_list(
            [
                "edit",
                "edit class-of-service",
                "edit traffic-control-profiles",
                f"delete {dcbmap}-tc{tc:d}-tcp",
                f"set {dcbmap}-tc{tc:d}-tcp scheduler-map " f"{dcbmap}-tc{tc:d}-smap",
            ]
        )
        sleep(2)
        self._connection.send_command(f"set {dcbmap}-tc{tc:d}-tcp guaranteed-rate percent {bw:d}")
        sleep(2)
        self._connection.send_command_list(["commit", "exit", "exit", "exit"])

    def get_dcb_map_bw_by_tc(self, dcbmap: str, tc: int) -> str:
        """
        Get the bandwidth percentage of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :return: Bandwidth value
        :raises ValueError: if parameters are invalid
        :raises SwitchException: if could not retrieve bandwidth percentage
        """
        if tc >= self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(f"Extreme switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:d} traffic classes.")

        output = self._connection.send_command(f"show class-of-service traffic-control-profile {dcbmap}-tc{tc:d}-tcp")
        lines = output.split("\n")
        if len(lines) < 2:
            raise SwitchException(f"Error retrieving bandwidth percentage for PG {tc}")
        for line in lines[1:]:
            if "Guaranteed rate:" in line:
                return line.split(" ")[4]
        raise SwitchException(f"Error retrieving bandwidth percentage for PG {tc}")

    def get_dcb_tc_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Retrieve traffic class by user priority for given port or dcb_map.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: assigned traffic class for user priority
        :raises ValueError: if parameters are invalid
        :raises SwitchException: if could not retrieve traffic class
        """
        if up not in range(8):
            raise ValueError("User priority has to be between 0 and 7.")

        output = self._connection.send_command(f"show class-of-service classifier name {dcbmap}-clsf")
        lines = output.split("\n")
        if len(lines) < 2:
            raise SwitchException("Error retrieving traffic class by user priority.")
        for line in lines[1:]:
            tc = any_match(line, rf"({decimal_to_bin(str(up))})\s+pg(\d)", flags=re.I)
            if tc:
                return tc[0][1]
        raise SwitchException("Error retrieving traffic class by user priority.")

    def get_dcb_bw_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Get bandwidth of DCB traffic class from the switch port.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: traffic class bandwidth percent
        """
        return str(self.get_dcb_map_bw_by_tc(dcbmap, int(self.get_dcb_tc_by_up(port, dcbmap, up))))
