# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Cisco NX-OS system."""

import logging
import re
from enum import Enum
from typing import Optional, List, Dict
from time import sleep
from mfd_common_libs import TimeoutCounter, add_logging_level, log_levels

from mfd_switchmanagement import CiscoAPIConnection
from mfd_switchmanagement.base import FecMode
from mfd_switchmanagement.exceptions import SwitchWaitForHoldingLinkStateTimeout, SwitchException
from mfd_switchmanagement.utils.match import any_match

from ..base import Cisco

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class NexusFecMode(Enum):
    """Available FEC modes for Cisco Nexus."""

    RS_FEC = "cl91"
    FC_FEC = "cl74"
    NO_FEC = "off"


class Cisco_NXOS(Cisco):
    """Commands base class for Cisco NX-OS system."""

    MINIMUM_FRAME_SIZE = 1523
    MAXIMUM_FRAME_SIZE = 9216
    PORT_REGEX = re.compile(r"^(Eth|Ethernet)(\d+/\d+(-\d+)?)?(\d+/\d+/\d+(-\d+)?)?$", re.I)

    def default_ports(self, ports: str) -> None:
        """
        Set ports to default configuration.

        :param ports: ports to configure
        """
        self._validate_port_and_port_channel_syntax(both_syntax=ports)

        commands = [
            "configure terminal",
            f"interface {ports}",
            "switchport trunk allowed vlan none",
            f"mtu {self.MAXIMUM_FRAME_SIZE}",
        ]
        self._connection.send_command_list(commands)
        self.shutdown(shutdown=False, port=ports)

    def configure_vlan(self, ports: str, vlan: int, vlan_type: str, mode: str) -> None:
        """
        Configure vlan.

        Set trunking and tagging mode, create vlan if required, enable port

        Supported ports: ethernet, port-channel
        :param ports: ports to configure
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :raises ValueError if parameters are invalid
        """
        self._validate_port_and_port_channel_syntax(both_syntax=ports)

        port_mode = mode.lower().strip()
        if port_mode == "access" or (port_mode == "trunk" and vlan_type == "untagged"):
            commands = [
                "configure terminal",
                f"vlan {vlan}",
                "exit",
                f"interface {ports}",
                "switchport mode trunk",
                f"switchport trunk native vlan {vlan}",
                f"switchport trunk allowed vlan add {vlan}",
            ]
        elif port_mode == "trunk" and vlan_type == "tagged":
            commands = [
                "configure terminal",
                f"vlan {vlan}",
                "exit",
                f"interface {ports}",
                "switchport mode trunk",
                f"switchport trunk allowed vlan add {vlan}",
            ]
        else:
            raise ValueError(f"Invalid mode or vlan type: {mode}, {vlan_type}")
        self._connection.send_command_list(commands)

    def get_port_by_mac(self, mac: str) -> str:
        """
        Get port with the specified MAC address.

        :param mac: mac address to find port
        :return: port name
        :raises SwitchException: if port not found
        :raises SwitchException: when mac not found
        :raises ValueError: if provided MAC address is incorrect
        """
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid mac address: {mac}")

        mac = self.change_standard_to_switch_mac_address(mac)
        commands = f"show mac address-table address {mac}"
        response = self._connection.send_command(commands)
        try:
            if isinstance(self._connection, CiscoAPIConnection):
                port = self._get_port_by_mac_by_api(mac, response)
            else:
                port = self._get_port_by_mac_by_console(response)
            return port
        except IndexError:
            raise SwitchException(f"Could not find MAC address {mac} on address-table.")

    def _get_vlan_by_mac_by_console(self, response: str) -> int:
        vlan = any_match(response, r"\**\s*(\d+)\s+\w{4}\.", flags=re.I)
        if vlan:
            return int(vlan[0])
        else:
            raise IndexError

    def _get_port_by_mac_by_console(self, response: str) -> str:
        port = any_match(response, r"(Eth\s*(:?\d+/){1,2}\d+(:?:\d+)*)(:?-(:?\d+/){1,2}\d+(:?:\d+)*)*", flags=re.I)
        if port:
            return port[0][0]
        else:
            raise IndexError

    def _get_port_by_mac_by_api(self, mac: str, response: Dict) -> int:
        body = self._verify_cisco_api_result(
            response, exception_message=f"Could not find MAC address {mac} on address-table."
        )
        mac_table = body.get("TABLE_mac_address", 0)
        if mac_table:
            if isinstance(mac_table["ROW_mac_address"], list):
                mac_table["ROW_mac_address"] = mac_table["ROW_mac_address"][0]
            port = mac_table["ROW_mac_address"].get("disp_port", 0)
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"found port {port}")
            return port

    def get_vlan_by_mac(self, mac: str) -> int:
        """
        Get VLAN of port with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: VLAN ID
        :raises SwitchException: if VLAN not found
        :raises SwitchException: when mac not found
        :raises ValueError: if provided MAC address is incorrect
        """
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid mac address: {mac}")

        mac = self.change_standard_to_switch_mac_address(mac)
        commands = f"show mac address-table address {mac}"
        response = self._connection.send_command(commands)
        try:
            if isinstance(self._connection, CiscoAPIConnection):
                vlan = self._get_vlan_by_mac_by_api(mac, response)
            else:
                vlan = self._get_vlan_by_mac_by_console(response)
            return vlan
        except IndexError:
            raise SwitchException(f"Could not find MAC address {mac} on address-table.")

    def _get_vlan_by_mac_by_api(self, mac: str, response: Dict) -> int:
        body = self._verify_cisco_api_result(
            response, exception_message=f"Could not find MAC address {mac} on address-table."
        )
        mac_table = body.get("TABLE_mac_address", 0)
        if isinstance(mac_table["ROW_mac_address"], list):
            mac_table["ROW_mac_address"] = mac_table["ROW_mac_address"][0]
        vlan = mac_table["ROW_mac_address"].get("disp_vlan", 0)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Found vlan {vlan}")
        return int(vlan)

    def _verify_cisco_api_result(self, response: Dict, *, exception_message: str) -> Dict:
        """
        Verify result correctness.

        :param response: Response from API
        :param exception_message: Body of exception
        :return: Body of result
        :raises SwitchException: if structure is incorrect
        :raises SwitchException: if result is empty
        """
        result = response[0].get("result")
        if result is None:
            raise SwitchException(exception_message)
        body = result.get("body", None)
        if body is None:
            raise SwitchException(f"Could not find correct structure ('body' section) in {result}")
        return body

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

    def _wait_for_holding_link_state(self, port: str, link_up: bool, timeout: int = 30) -> None:
        """
        Wait timeout time if the link is holding expected state (up or down).

        :param link_up: True for link up, False for link down checking
        :param timeout: Timeout to wait for link to come up or down, in seconds.
        :raises SwitchWaitForLinkStateTimeout: If link didn't come up before timeout happened.
        """
        timeout_state = TimeoutCounter(timeout)
        condition = True if link_up else False
        time_for_holding_state = timeout / 2
        counter = TimeoutCounter(time_for_holding_state)
        while not timeout_state:
            if not self.is_port_linkup(port=port) == condition:
                counter = TimeoutCounter(time_for_holding_state)  # start counter again, link is flapping
            if counter:
                return
            sleep(0.1)
        raise SwitchWaitForHoldingLinkStateTimeout()

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set the DCBX version for the switch port.

        :param port: switch port in Extreme format
        :param mode: DCBX mode
        :raises ValueError if parameters are invalid
        """
        mode = mode.lower()
        if mode not in {"cee", "ieee"}:
            raise ValueError("Invalid DCBX value, must be either 'CEE' or 'IEEE'")

        self._validate_configure_parameters(ports=port)

        commands = ["configure terminal", f"interface {port}", f"lldp dcbx version {mode}"]
        self._connection.send_command_list(commands)
        self.shutdown(shutdown=True, port=port)

        self._wait_for_holding_link_state(port=port, link_up=False, timeout=3)  # prevent link flap

        self.shutdown(shutdown=False, port=port)

        self._wait_for_holding_link_state(port=port, link_up=True, timeout=10)

    def clear_port_dcbx(self, port: str) -> None:
        """
        Clear dcbx of port.

        :param port: port to configure
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        commands = [
            "configure terminal",
            f"interface {port}",
            "no lldp dcbx version cee",
            "no lldp dcbx version ieee",
        ]
        self._connection.send_command_list(commands)
        self.shutdown(shutdown=True, port=port)

        self._wait_for_holding_link_state(port=port, link_up=False, timeout=5)  # prevent link flap

        self.shutdown(shutdown=False, port=port)

        self._wait_for_holding_link_state(port=port, link_up=True, timeout=10)

    def show_port_dcbx(self, port: str) -> str:
        """
        Show dcbx configuration including peer info.

        :param port: port
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"show lldp dcbx interface {port}")
        return output

    def set_port_pfc_by_tc(self, port: str, qos_priority: Optional[int], pfc: str) -> None:
        """
        Configure PFC settings.

        :param port: port
        :param qos_priority: QoS priority (0 ~ 7) (not used for Cisco, PFC must be configured per whole switch)
        :param pfc: PFC state
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        pfc = pfc.lower()
        if pfc not in {"on", "off", "auto"}:
            raise ValueError("Invalid PFC value, must be either 'on', 'off' or 'auto'")

        commands = ["configure terminal", f"interface {port}", f"priority-flow-control mode {pfc}"]
        self._connection.send_command_list(commands)

    def delete_port_pfc(self, port: str) -> None:
        """
        Delete the PFC settings.

        :param port: ports
        """
        self.set_port_pfc_by_tc(port=port, qos_priority=-1, pfc="auto")

    def set_port_bw_by_tc(self, port: str, bandwidth: List = None, suffix: Optional[str] = "") -> None:
        """
        Set the bandwidth of traffic class on a selected port.

        :param port: switch port
        :param bandwidth: list of bandwidth (not used)
        :param suffix: suffix for names
        """
        self._validate_configure_parameters(ports=port)

        commands = [
            "configure terminal",
            f"interface {port}",
            f"service-policy type qos input QOS_{suffix}",
            f"service-policy type queuing input IN_{suffix}",
        ]
        self._connection.send_command_list(commands)

    def delete_port_bw_by_tc(self, port: str, suffix: Optional[str] = "") -> None:
        """
        Delete the bandwidth of traffic class on a selected port.

        :param port: switch port
        :param suffix: suffix for names
        """
        self._validate_configure_parameters(ports=port)

        commands = [
            "configure terminal",
            f"interface {port}",
            f"no service-policy type qos input QOS_{suffix}",
            f"no service-policy type queuing input IN_{suffix}",
        ]
        self._connection.send_command_list(commands)

    def create_qos_policy(self, bandwidth: List, up2tc: List, suffix: Optional[str] = "") -> None:
        """
        Create QOS policy.

        :param bandwidth: list of bandwidth per traffic class
        :param up2tc: list of assignment of QoS priority to traffic class
        :param suffix: suffix to use in names
        """
        commands = ["configure terminal", f"policy-map type queuing IN_{suffix}"]
        for i, bandwidth in enumerate(bandwidth):
            if bandwidth > 0:
                queue = f"c-in-q{i}" if i > 0 else "c-in-q-default"
                commands.append(f"class type queuing {queue}")
                commands.append(f"bandwidth percent {bandwidth}")

        self._connection.send_command_list(commands)

        configuration_commands = ["configure terminal"]
        policy_commands = ["configure terminal", f"policy-map type qos QOS_{suffix}"]
        for i in self.QOS_PRIORITY:
            if i in up2tc:
                cos_value = ",".join([str(qos_prio) for qos_prio, tc in enumerate(up2tc) if tc == i])
                configuration_commands.append(f"class-map type qos match-all TC{i}_{suffix}")
                configuration_commands.append(f"match cos {cos_value}")

                policy_commands.append(f"class TC{i}_{suffix}")
                policy_commands.append(f"set qos-group {i}")

        self._connection.send_command_list(configuration_commands)
        self._connection.send_command_list(policy_commands)

    def delete_qos_policy(self, suffix: Optional[str] = "") -> None:
        """
        Delete the policy for QOS.

        :param suffix: to use in names
        """
        commands = [
            "configure terminal",
            f"no policy-map type qos QOS_{suffix}",
            f"no policy-map type queuing IN_{suffix}",
        ]
        for i in self.QOS_PRIORITY:
            commands.append(f"no class-map type qos match-all TC{i}_{suffix}")

        self._connection.send_command_list(commands)

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        :raises SwitchException when state of port can't be read, there is problem with parsing output and when response
                is not correct.
        :raises SwitchException when port is incorrect
        """
        if isinstance(self._connection, CiscoAPIConnection):
            return self._is_port_linkup_by_api(port=port)
        else:
            return self._is_port_linkup_by_console(port=port)

    def _is_port_linkup_by_console(self, port: str) -> bool:
        """

        Use any console connection, check if indicated port is "UP".

        :param port: port of switch
        :return: Status of link
        :raises SwitchException when output doesn't contain "up" or "down" state of port.
        """
        comm = f"show ip int brief {port}"
        output = self._connection.send_command(comm)
        if "down" in output:
            return False
        elif "up" in output:
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")

    def _is_port_linkup_by_api(self, port: str) -> bool:
        """
        Use requests to API, check if indicated port is "UP".

        :param port: port of switch
        :return: Status of link
        :raises SwitchException when state of port can't be read, there is problem with parsing output and when json
                structure of response is not correct.
        """
        comm = f"show interface {port} brief"
        response = self._connection.send_command(comm)
        try:
            body = self._verify_cisco_api_result(
                response, exception_message=f"Could not find port {port} in switch interfaces."
            )
            interface_table = body.get("TABLE_interface", 0)
            if interface_table:
                if isinstance(interface_table["ROW_interface"], list):
                    interface_table["ROW_interface"] = interface_table["ROW_interface"][0]
                port_state = interface_table["ROW_interface"].get("state", 0)
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"port {port} state {port_state}")
                if "down" in port_state:
                    return False
                elif "up" in port_state:
                    return True
                else:
                    raise SwitchException(f"Unable to read state of': {self.__class__.__name__}; interface: {port})")
            else:
                raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")
        except IndexError:
            raise SwitchException(f"State of port: {port} not found, API response may be corrupted.")

    def _prepare_port_configuration(self, port: str) -> str:
        return self._connection.send_command_list(["conf t", f"int {port}", "switchport"])

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
            [
                "switchport mode access",
                "no switchport trunk allowed vlan",
                f"switchport access vlan {vlan}",
                "no sh",
                "spanning-tree port type edge",
            ]
        )

    def set_fec(self, port: str, fec_mode: FecMode) -> None:
        """
        Set Forward error correction on port.

        :param port: port of switch
        :param fec_mode: Value of FEC
        :raises SwitchException on failure
        """
        self._prepare_port_configuration(port)
        output = self._connection.send_command(f"fec {fec_mode}")
        if output.find("requested config change not allowed") != -1:
            raise SwitchException(f"Unable to set FEC on port {port}. Potential issue: wrong media inserted.")

    def get_fec(self, port: str) -> str:
        """
        Get Forward error correction on port.

        :param port: port of switch
        :return: FEC Mode
        """
        port_cfg = self.show_port_running_config(port)
        if port_cfg.find(f"fec {FecMode.RS_FEC.value}") != -1:
            return FecMode.RS_FEC.value
        if port_cfg.find(f"fec {FecMode.NO_FEC.value}") != -1:
            return FecMode.NO_FEC.value
        if port_cfg.find(f"fec {FecMode.FC_FEC.value}") != -1:
            return FecMode.FC_FEC.value

        raise SwitchException(f"Error while checking FEC on port: {port}")

    def is_fec_mode_set(self, port: str, fec_mode: FecMode) -> bool:
        """
        Check if fec is set.

        :param port: port of switch
        :param fec_mode: Value of FEC
        :return: status
        """
        return self.get_fec(port) == fec_mode.value

    @staticmethod
    def _validate_port_channel_no(pc_no: int) -> None:
        """Validate port channel number.

        :param pc_no: number of port channel
        :raises: ValueError if port-channel number is out of accepted range.
        """
        if pc_no not in range(1, 4097):
            raise ValueError("Port channel interface number should be integer in range 1-4096")

    def create_port_channel_interface(self, pc_no: int) -> None:
        """Create port channel interface with given number.

        :param pc_no: number of port channel
        """
        self._validate_port_channel_no(pc_no)
        commands = ["configure terminal", f"interface port-channel {pc_no}"]
        self._connection.send_command_list(commands)

    def remove_port(self, port: str) -> None:
        """Remove port from switch.

        Supported ports: port-channel
        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(port_channel=port)
        commands = ["configure terminal", f"no interface {port}"]
        self._connection.send_command_list(commands)

    def show_port_channel_summary(self, pc_no: Optional[int] = None) -> str:
        """Show summary for port channel interface.

        :param pc_no: number of port channel
        """
        command = "show port-channel summary"
        if pc_no:
            command += f" interface port-channel {pc_no}"
        return self._connection.send_command(command)

    def set_switchport_mode(self, port: str, mode: str) -> None:
        """Set switchport mode.

        Supported ports: ethernet, port-channel
        :param port: port of switch
        :param mode: switchport mode
        :raises ValueError when switchport mode is incorrect
        """
        self._validate_port_and_port_channel_syntax(both_syntax=port)
        if mode not in ["access", "dot1q-tunnel", "fex-fabric", "trunk"]:
            raise ValueError("Incorrect switchport mode")

        commands = ["configure terminal", f"interface {port}", f"switchport mode {mode}"]
        self._connection.send_command_list(commands)

    def add_port_to_channel_group(
        self, port: str, pc_no: int, *, force: Optional[bool] = None, mode: Optional[str] = None
    ) -> None:
        """Add ethernet port to port channel group.

        Supported ports: ethernet
        :param port: port of switch
        :param pc_no: MTU size
        :param force: Force settings from port-channel to be applied on provided ports
        :param mode: LACP mode
        :raises ValueError when mode is incorrect
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        self._validate_port_channel_no(pc_no)
        allowed_mode_values = ["active", "on", "passive"]

        commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no}"]
        if force:
            commands[2] += " force"

        if mode:
            if mode not in allowed_mode_values:
                raise ValueError(f"{mode} is incorrect parameter for channel-group mode")
            commands[2] += f" mode {mode}"

        self._connection.send_command_list(commands)

    def set_lacp_rate(self, port: str, rate: str) -> None:
        """Set LACP rate on port.

        Supported ports: ethernet
        :param port: port of switch
        :param rate: rate of lacp frames
        :raises ValueError when rate is incorrect
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        allowed_values = ["fast", "normal"]
        if rate not in allowed_values:
            raise ValueError(f"{rate} is incorrect option for LACP rate")

        commands = ["configure terminal", f"interface {port}", f"lacp rate {rate}"]
        self._connection.send_command_list(commands)

    def disable_lacp_rate(self, port: str) -> None:
        """Disable LACP rate on port.

        Supported ports: ethernet
        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        commands = ["configure terminal", f"interface {port}", "no lacp rate"]
        self._connection.send_command_list(commands)
