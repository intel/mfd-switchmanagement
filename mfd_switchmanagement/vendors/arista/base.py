# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Arista base."""

import logging
import re
from enum import Enum
from typing import Any, Iterable
from mfd_common_libs import add_logging_level, log_levels

from ...base import Switch
from ...utils.match import any_match
from ...exceptions import SwitchException

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class FecMode(Enum):
    """Available FEC modes."""

    RS_FEC = "reed-solomon"
    FC_FEC = "fire-code"
    NO_FEC = "disabled"


class Arista(Switch):
    """
    Base class for Arista type switch.

    based on Arista DCS-7050Q switch
    """

    MINIMUM_FRAME_SIZE = 68
    MAXIMUM_FRAME_SIZE = 9214
    DEFAULT_INTERFACE_NAME = "ethernet "
    PORT_REGEX = re.compile(
        r"^(e(t(h|hernet)?)?)\d+/\d+(/\d+)?(-\d+)?(,(e(t(h|hernet)?)?)\d+/\d+(/\d+)?(-\d+)?){0,4}$", re.I
    )
    PORT_CHANNEL_REGEX = re.compile(r"^port-channel(\s+\d+(,\s*\d+)*)?$", re.A | re.I)
    ERROR_CORRECTION_REGEX = re.compile(r"(\S+\s+){3}(?P<operational>\S+)")

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        Supported ports: ethernet, port-channel
        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(both_syntax=port)

        prefix = "" if shutdown else "no "
        commands = ["configure terminal", f"interface {port}", f"{prefix}shutdown"]
        self._connection.send_command_list(commands)

    def enable_port(self, port: str, count: int = 1) -> None:
        """
        Enable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        for _ in range(count):
            self.shutdown(False, port)

    def disable_port(self, port: str, count: int = 1) -> None:
        """
        Disable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        for _ in range(count):
            self.shutdown(True, port)

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Arista Switch."""
        return self.MAXIMUM_FRAME_SIZE

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
            output = self._connection.send_command(f"sh mac address-table address {mac.upper()}")
            port = any_match(output, r"((Et|Ethernet)\d+(/\d+)*)", flags=re.I)
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
            output = self._connection.send_command(f"sh mac address-table address {mac.upper()}")
            """
            Arista-1A>show mac address-table
              Mac Address Table
                ------------------------------------------------------------------

                Vlan    Mac Address       Type        Ports      Moves   Last Move
                ----    -----------       ----        -----      -----   ---------
                   1    0000.0000.0314    DYNAMIC     Et11/3     1       27 days, 20:34:21 ago
                   1    0000.0000.0315    DYNAMIC     Et11/4     1       27 days, 20:34:21 ago
                   1    0000.0000.0316    DYNAMIC     Et11/2     1       27 days, 20:34:21 ago
            """
            vlan = any_match(output, r"(\d+)\s+\w{4}\.", flags=re.I)
            if vlan:
                return int(vlan[0])
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        """
        port = self.get_port_by_mac(mac)
        if port:
            match = re.search(r"(?:Et|Ethernet)?(\d+/\d+)", port, re.I)
            if match:
                self._connection.send_command(f"clear mac address-table dynamic interface ethernet {match.group(1)}")

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Enable jumbo frame.

        :param frame_size: Size of frame
        :param port: port of switch
        :raises ValueError if parameters are invalid
        """
        if frame_size < self.MINIMUM_FRAME_SIZE or frame_size > self.MAXIMUM_FRAME_SIZE:
            raise ValueError(
                f"Invalid frame size {frame_size}. "
                f"Valid values are '{self.MINIMUM_FRAME_SIZE}' to '{self.MAXIMUM_FRAME_SIZE}'"
            )

        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        self._connection.send_command(f"mtu {frame_size}")

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: port of switch
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        self._connection.send_command("no mtu")

    def configure_vlan(self, ports: str, vlan: int, vlan_type: str, mode: str, override_allowed: bool = False) -> None:
        """
        Configure vlan.

        Set trunking and tagging mode, create vlan if required, enable port

        :param ports: ports to configure
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :param override_allowed: if True, provided vlan overrides allowed vlans
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
                command_list.append(f"switchport trunk allowed vlan {'' if override_allowed else 'add '}{vlan:d}")
            if vlan_type.lower().strip() == "untagged":
                command_list.append(f"switchport trunk native vlan {vlan:d}")
            command_list.append("switchport mode trunk")
            command_list.append("spanning-tree portfast trunk")
        command_list.append("no shutdown")
        self._connection.send_command_list(command_list)

    def remove_vlan(self, vlan: int) -> bool:
        """
        Remove vlan from switch.

        :param vlan: Vlan to delete
        :return: Status of remove
        :raises ValueError if parameters are invalid
        """
        if vlan == 1:  # Should not remove the default VLAN
            raise ValueError("Should not remove the default VLAN.")
        elif not vlan:
            raise ValueError("VLAN Id must be specified.")

        self._connection.send_configuration([f"no vlan {vlan}"])

        # verify VLAN is completely removed
        output = self._connection.send_command(f"show vlan {vlan}")
        return f"vlan {vlan} not found" in output.lower()

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        Restore speed of port (breakout feature) if required.
        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)
        speed_command = self._get_speed_command_from_configuration(ports)
        self._connection.send_command_list(
            [
                "configure terminal",
                f"default interface {ports}",
                f"interface {ports}",
                "default switchport",
                "default mtu",
                f"{speed_command}",
            ]
        )

    def _get_speed_command_from_configuration(self, port: str) -> str:
        """Read speed configuration command from running-conf."""
        output = self._connection.send_command(f"show running-config interfaces {port}")
        speed_command = re.search(r"^\s*(?P<speed>speed .*)$", output, re.M)
        if speed_command:
            return speed_command.group("speed")
        else:
            return ""

    def get_port_speed(self, port: str) -> int:  # noqa W102
        self._validate_configure_parameters(ports=port)

        gigabit_multiplier = 1000
        cmd = f"show interfaces {port} status"
        output = self._connection.send_command(cmd)
        speed = re.search(r"(?P<speed>\d+)G\s", output, re.M)
        if speed:
            return int(speed.group("speed")) * gigabit_multiplier
        else:
            raise SwitchException(f"Couldn't retrieve port speed for port: {port} in output: {output}")

    def is_fec_enabled(self, port: str) -> bool:
        """
        Check on given port whether Forward Error Correction is enabled or not.

        :param port: port of switch
        :return: True if FEC is enabled, False otherwise.
        :raises: SwitchException if it cannot recognize output for error-correction
        """
        self._prepare_port_configuration(port)
        out = self._connection.send_command_list([f"show interface {port} error-correction", "end"])
        match = re.findall(self.ERROR_CORRECTION_REGEX, out)
        if match:
            return bool(match[-1][-1].casefold() != FecMode.NO_FEC.value)
        raise SwitchException("Cannot recognize Forward Error Correction status")

    def disable_fec(self, port: str) -> bool:
        """
        Enable Set Forward Error Correction on port.

        :param port: port of switch
        :return: True if FEC was disabled, False otherwise.
        :raises: SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["no error-correction encoding", "end"])
        return not self.is_fec_enabled(port)

    def enable_fec(self, port: str) -> bool:
        """
        Enable Set Forward Error correction on port.

        :param port: port of switch
        :return: True if FEC was enabled, False otherwise.
        :raises: SwitchException on failure
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["error-correction encoding open", "end"])
        return self.is_fec_enabled(port)

    def get_fec_hardware(self, port: str) -> str:
        """
        Get Forward error correction on port.

        :param port: port of switch
        """
        self._prepare_port_configuration(port)
        out = self._connection.send_command_list([f"show interfaces {port} hardware", "end"])
        match = re.search(r"Error\s+correction:\s+(\S+)\s+(\S+)\s+(\S+)", out)
        if match:
            return match.group()

    def get_fec(self, port: str) -> str:
        """
        Get Forward error correction on port.

        :param port: port of switch
        :return: string with operational mode from FecMode Enum
        """
        self._prepare_port_configuration(port)
        out = self._connection.send_command_list([f"show interface {port} error-correction", "end"])
        match = re.findall(self.ERROR_CORRECTION_REGEX, out)
        if match:
            operational_mode = match[-1][-1].casefold()
            if operational_mode in [mode.value for mode in FecMode]:
                return operational_mode
        raise SwitchException(f"Cannot recognize Forward Error Correction operational status in {out}")

    def show_vlans(self, vlans: Iterable[Any] = None) -> str:
        """
        Show provided or all vlans configuration.

        :param vlan: iterable with particular vlans to show
        :return: vlans information
        """
        return self._connection.send_command(f"show vlan{(' ' + ','.join(map(str, vlans))) if vlans else ''}")

    @staticmethod
    def _validate_port_channel_no(pc_no: int) -> None:
        """Validate port channel number.

        :param pc_no: number of port channel
        :raises: ValueError if port-channel number is out of accepted range.
        """
        if pc_no not in range(1, 2001):
            raise ValueError("Port channel interface number should be integer in range 1-2000")

    def create_port_channel_interface(self, pc_no: int) -> None:
        """Create port channel interface with given number.

        :param pc_no: number of port channel
        """
        self._validate_port_channel_no(pc_no)
        commands = ["configure terminal", f"interface port-channel {pc_no}", "end"]
        self._connection.send_command_list(commands)

    def remove_port(self, port: str) -> None:
        """Remove port from switch.

        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(port_channel=port)
        commands = ["configure terminal", f"no interface {port}", "end"]
        self._connection.send_command_list(commands)

    def add_port_to_channel_group(self, port: str, pc_no: int, mode: str) -> None:
        """Add ethernet port to port channel group.

        :param port: port of switch
        :param pc_no: number of port channel interface
        :param mode : LACP mode
        :raises ValueError when mode is incorrect
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        self._validate_port_channel_no(pc_no)
        allowed_mode_values = ["active", "on", "passive"]
        commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no}", "end"]

        if mode:
            if mode not in allowed_mode_values:
                raise ValueError(f"{mode} is incorrect parameter for channel-group mode")
            commands[2] += f" mode {mode}"

        self._connection.send_command_list(commands)

    def remove_port_from_port_channel(self, port: str) -> None:
        """
        Remove port from the specified port-channel.

        :param port: port of the switch
        """
        self._prepare_port_configuration(port)
        self._connection.send_command_list(["no channel-group", "end"])

    def show_port_channel(self, port_channel: str = None) -> None:
        """
        Show port-channel.

        :param port_channel: port_channel (eg. "port-channel 100")
        """
        self._validate_port_and_port_channel_syntax(port_channel=port_channel)
        return self._connection.send_command(f"show {port_channel or 'port-channel'}")

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        return self._connection.send_command(f"show running-config interfaces {port}")

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        output = self._connection.send_command(f"show interfaces {port} mac")
        if "linkdown" in output.lower():
            return False
        elif "linkup" in output.lower():
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port}")

    def configure_dcbx_ets_traffic_class(self, class_bandwidth: dict[int, int], *, disable: bool = False) -> None:
        """
        Configure DCBX ETS traffic class settings on the switch.

        :param class_bandwidth: Dictionary mapping traffic class (1-8) to bandwidth percentage (0-100)
        :param disable: If True, disables the ETS traffic class configuration
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring DCBX ETS traffic class: {class_bandwidth}")
        commands = []
        for traffic_class, bandwidth in class_bandwidth.items():
            if traffic_class not in range(1, 9):
                raise ValueError("Traffic class must be between 1 and 8.")
            if bandwidth not in range(0, 101):
                raise ValueError("Bandwidth must be between 0 and 100.")
            commands.append(f"{'no ' if disable else ''}dcbx ets traffic-class {traffic_class} bandwidth {bandwidth}")
        self._connection.send_configuration(commands)

    def configure_dcbx_qos_map(self, cos_to_tc_map: dict[int, int], disable: bool = False) -> None:
        """
        Configure DCBX QoS map settings on the switch.

        :param cos_to_tc_map: Dictionary mapping CoS (0-7) to traffic class (1-8)
        :param disable: If True, disables the QoS map configuration
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring DCBX QoS map: {cos_to_tc_map}")
        commands = []
        for cos, traffic_class in cos_to_tc_map.items():
            if cos not in range(0, 8):
                raise ValueError("CoS must be between 0 and 7.")
            if traffic_class not in range(1, 9):
                raise ValueError("Traffic class must be between 1 and 8.")
            commands.append(f"{'no ' if disable else ''}dcbx ets qos map cos {cos} traffic-class {traffic_class}")
        self._connection.send_configuration(commands)

    def configure_dcbx(
        self, cos_to_tc_map: dict[int, int] | None = None, class_bandwidth: dict[int, int] | None = None
    ) -> None:
        """
        Configure DCBX settings on the switch.

        :param cos_to_tc_map: Dictionary mapping CoS (0-7) to traffic class (1-8), defaults to {3: 1}
        :param class_bandwidth: Dictionary mapping traffic class (1-8) to bandwidth percentage (0-100)
            defaults to {1: 100}
        """
        if cos_to_tc_map is None:
            cos_to_tc_map = {3: 1}
        if class_bandwidth is None:
            class_bandwidth = {1: 100}
        self.configure_dcbx_qos_map(cos_to_tc_map)
        self.configure_dcbx_ets_traffic_class(class_bandwidth)

    def configure_lldp(self, port: str) -> None:
        """
        Configure LLDP settings on the interface.

        :param port: port of switch
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring LLDP on port: {port}")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"interface {port}",
            "lldp transmit",
            "lldp receive",
        ]
        self._connection.send_configuration(commands)

    def configure_trunking(self, port: str) -> None:
        """
        Configure trunking settings on the interface.

        :param port: port of switch
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring trunking on port: {port}")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"interface {port}",
            "switchport mode trunk",
            "switchport trunk allowed vlan all",
        ]
        self._connection.send_configuration(commands)

    def configure_dcbx_mode(self, port: str, mode: str = "ieee") -> None:
        """
        Configure DCBX mode on the interface.

        :param port: port of switch
        :param mode: DCBX mode to set, default is "ieee"
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring DCBX mode on port: {port} to {mode}")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"interface {port}",
            f"dcbx mode {mode.lower()}",
        ]
        self._connection.send_configuration(commands)

    def disable_flowcontrol(self, port: str) -> None:
        """
        Disable flow control on the interface.

        :param port: port of switch
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Disabling flow control on port: {port}")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"interface {port}",
            "flowcontrol send off",
            "flowcontrol receive off",
        ]
        self._connection.send_configuration(commands)

    def configure_priority_flow_control(self, port: str, priorities: list[int] | None = None) -> None:
        """
        Prepare priority flow control settings on the interface.

        :param port: port of switch
        :param priorities: list of priority levels to configure, defaults to [3, 0, 1, 2, 4, 5, 6]
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configuring PFC on port: {port} with priorities: {priorities}")
        if priorities is None:
            priorities = [3, 0, 1, 2, 4, 5, 6]
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"interface {port}",
            "priority-flow-control mode on",  # can be deprecated in future versions of switch
            "priority-flow-control on",
        ]
        for priority in priorities:
            commands.append(f"priority-flow-control priority {priority} no-drop")
        self._connection.send_configuration(commands)

    def configure_pfc_userspace(self, port: str) -> None:
        """
        Configure default Priority Flow Control (PFC) settings on the interface.

        :param port: port of switch
        """
        self.configure_dcbx()
        self.configure_lldp(port)
        self.configure_trunking(port)
        self.configure_dcbx_mode(port)
        self.disable_flowcontrol(port)
        self.configure_priority_flow_control(port)

    def disable_pfc_userspace(self, port: str) -> None:
        """
        Disable Priority Flow Control (PFC) settings on the interface.

        :param port: port of switch
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Disabling PFC on port: {port}")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = [
            f"default interface {port}",
        ]
        self._connection.send_configuration(commands)
        self.configure_dcbx_ets_traffic_class(class_bandwidth={1: 100}, disable=True)
        self.configure_dcbx_qos_map(cos_to_tc_map={3: 1}, disable=True)
