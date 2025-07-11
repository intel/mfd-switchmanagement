# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Mellanox base."""

import re
from typing import List

from ...base import Switch
from ...base import LLDPlink
from ...data_structures import State, ETSMode
from ...exceptions import SwitchException
from ...utils.match import any_match


class Mellanox(Switch):
    """Base implementation for Mellanox switch."""

    PORT_REGEX = re.compile(r"(?P<interface>eth|ethernet)\s?(?P<port_number>\d+/\d+(/\d+)?)", re.I)
    DEFAULT_INTERFACE_NAME = "ethernet "
    MINIMUM_FRAME_SIZE = 1518
    DEFAULT_MTU_FRAME_SIZE = 9200
    MAXIMUM_SUPPORT_TRAFFIC_CLASSES = 8
    INVALID_PORT_FORMAT_MESSAGE = "Invalid port list: Valid port list format is eth<unit#>/<slot#>(/<port#>),"

    def _extract_port_number(self, port: str) -> str:
        """
        Extract the port number from the given port string.

        :param port: Port string in the format 'eth<unit#>/<slot#>(/<port#>)'
        :return: Extracted port number in the format '<unit#>/<slot#>(/<port#>)'
        """
        port_match = self.PORT_REGEX.search(port)
        if not port_match:
            raise ValueError(f"Invalid port format: {port}")
        return port_match.group("port_number")

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Mellanox Switch."""
        return self.DEFAULT_MTU_FRAME_SIZE

    def show_ports_status(self) -> str:
        """
        Show all ports status.

        :return: Ports information
        """
        return self._connection.send_command("show interfaces ethernet status")

    def _prepare_port_configuration(self, port: str) -> str:
        """
        Prepare port to configuration.

        :param port: port to configure
        """
        port_match = self.PORT_REGEX.search(port)
        self._connection.exit_port_configuration()
        return self._connection.send_command_list(["conf t", f"interface ethernet {port_match.group('port_number')}"])

    def enable_spanning_tree(self, port: str) -> str:
        """
        Enable spanning tree on given port.

        :param port: port of switch
        :return: Output from enabling
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        return self._connection.send_command_list(["spanning-tree port type edge", "spanning-tree bpdufilter disable"])

    def disable_spanning_tree(self, port: str) -> str:
        """
        Disable spanning tree on given port.

        :param port: port of switch
        :return: Output from disabling
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        return self._connection.send_command(["no spanning-tree port type", "spanning-tree bpdufilter enable"])

    def disable_port(self, port: str, count: str = 3) -> str:
        """
        Disable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        return self._connection.send_command("shu")

    def change_vlan(self, port: str, vlan: int) -> str:
        """
        Change Vlan port and switches mode to access.

        :param port: port of switch
        :param vlan: vlan to set
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            [
                "no switchport mode",
                "switchport",
                "switchport mode access",
                f"switchport access vlan {vlan}",
                "no sh",
                "spanning-tree port type edge",
            ]
        )

    def set_trunking_interface(self, port: str, vlan: int) -> str:
        """
        Change mode to trunk on port and allows vlan traffic on this port.

        :param port: port of switch
        :param vlan: vlan to set
        :return: Output from setting
        """
        self._validate_configure_parameters(ports=port)

        self._prepare_port_configuration(port)
        return self._connection.send_command_list(
            [
                "no switchport mode",
                "switchport",
                "switchport mode trunk",
                f"switchport trunk allowed-vlan {vlan}",
                f"switchport trunk allowed-vlan add {vlan}",
                "no sh",
            ]
        )

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        running_cfg = self._connection.send_command("show running-config")
        running_cfg = running_cfg.split("\n")

        port_cfg = []
        for line in running_cfg:
            if re.search(rf"\b{port}\b", line):
                port_cfg.append(line.lstrip())
        port_cfg = "\n".join(set(port_cfg))  # to eliminate duplicates
        return port_cfg

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        all_ports = self.show_ports_status()
        lines = all_ports.split("\n")
        for line in lines:
            if port.lower() in line.lower():
                if "up" in line.lower() and "down" not in line.lower():
                    return True
                elif "down" in line.lower() and "up" not in line.lower():
                    return False
                else:
                    raise SwitchException(
                        f"Link status parsing error on: {self.__class__.__name__}; " f"interface: {port})"
                    )
        raise SwitchException(f"No such interface ({port}) on: {self.__class__.__name__}")

    def change_standard_to_switch_mac_address(self, address: str) -> str:
        """
        Convert standard mac address to switch mac address format.

        :param address: any mac address (no separators, separated using -:., lowecase, uppercase etc.
        :return: MAC address in switch accepted format (AA:BB:CC:DD:EE:FF)
        """
        a = r"([a-f0-9]{2})"
        double_regex = re.compile(rf"{a}{a}{a}{a}{a}{a}")
        hex_bytes = address.lower()

        for c in ":.-":
            hex_bytes = hex_bytes.replace(c, "")

        return ":".join(double_regex.match(hex_bytes).groups())

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
            output = self._connection.send_command(f"show mac-address-table address {mac.upper()}")
            port = self.PORT_REGEX.search(output)
            if port:
                return port.group()
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
            output = self._connection.send_command(f"show mac-address-table address {mac.upper()}")
            vlan = any_match(output, r"^\d+\s+\w{2}:", flags=re.I)
            if vlan:
                return int(vlan[0].split()[0])
            else:
                raise SwitchException(f"Could not find VLAN for MAC address {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        :raises ValueError: if provided MAC address is incorrect
        :raises ValueError: if port number not found
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            port = self.get_port_by_mac(mac)
            if port:
                port_match = self.PORT_REGEX.search(port)
                self._connection.send_command(
                    f"clear mac-address-table dynamic interface ethernet {port_match.group('port_number')}"
                )
            else:
                raise ValueError(f"Couldn't find port number for MAC address: {mac}")
        else:
            raise ValueError(f"Incorrect MAC address: {mac}")

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)
        port_match = self.PORT_REGEX.search(ports)
        self._connection.send_command_list(
            [
                "configure terminal",
                f"interface ethernet {port_match.group('port_number')}",
                "no shutdown",
                f"mtu {self.DEFAULT_MTU_FRAME_SIZE:d} force",
                "switchport mode hybrid",
                "switchport hybrid allowed-vlan all",
                "no dcb priority-flow-control mode force",
                "exit",
                "exit",
            ]
        )

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
        port_match = self.PORT_REGEX.search(ports)
        command_list = [
            "configure terminal",
            f"interface ethernet {port_match.group('port_number')}",
            "no shutdown",
            f"switchport hybrid allowed-vlan {vlan}",
            "exit",
            "exit",
        ]
        self._connection.send_command_list(command_list)

    def get_lldp_port(self, mac: str) -> str:
        """
        Get the lldp switch port of an adapter with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: switch port
        """
        return self.get_port_by_mac(mac)

    def get_lldp_neighbors(self) -> List[LLDPlink]:
        """
        Get the lldp neighbors for switch.

        :return: list of LLDPlinks
        """
        links = []

        output = self._connection.send_command("show lldp remote")
        neighbor_regex = (
            r"^(?P<local_interface>Eth[\d\/]+)\s{2,}"
            r"(?P<device_id>\S+)\s{2,}"
            r"(?P<port_id>\S+\s?\S+)\s{2,}"
            r"(?P<system_name>\S+\s?\S+)$"
        )

        for match in re.finditer(neighbor_regex, output, re.MULTILINE):
            links.append(
                LLDPlink(
                    loc_portid=match.group("local_interface"),
                    rem_sysname=match.group("system_name"),
                    rem_portid=match.group("port_id"),
                    rem_devid=match.group("device_id"),
                )
            )

        return links

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set dcbx version of port.

        :param port: port to configure
        :param mode: version
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        dcbx = any_match(mode, r"(\bCEE|\bIEEE)", flags=re.I)
        if not dcbx:
            raise ValueError(""" Invalid DCBX value, must be either 'CEE' or 'IEEE'""")
        self._connection.send_command_list(
            [
                "configure terminal",
                f"interface ethernet {port_number}",
                f"lldp tlv-select " f'dcbx{"" if "ieee" == mode.lower() else "-cee"}',
                "exit",
                "exit",
            ]
        )

    def set_dcb_qos_conf(self, port: str, dcbmap: str, dcb_tc_info_list: List) -> None:
        """
        Configure DCB traffic on the switch port.

        :param port: port of switch
        :param dcbmap: switch DCB map name to assign
        :param dcb_tc_info_list: DCB traffic class info list.
        length of list has to be 3 or less (str traffic_class, str bandwidth, str pfc='off')
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        if len(dcb_tc_info_list) > self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(
                f"Mellanox switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:d} traffic classes."
            )
        command_list = ["configure terminal", f"interface ethernet {port_number}"]

        available_bw = 100
        tcs = [str(tc) for tc in range(0, 8)]
        for info in dcb_tc_info_list:
            command_list.append(f"traffic-class {info[0]} dcb ets wrr {info[1]}")
            tcs.remove(info[0])
            available_bw -= int(info[1])
            if available_bw <= 0:
                raise ValueError(""" Total bandwidth percent cannot be exceed 100. """)
        bw_to_assign = int(available_bw / len(tcs))
        for tc in tcs:
            if tc != "7":
                command_list.append(f"traffic-class {tc[0]} dcb ets wrr {bw_to_assign:d}")
            else:
                command_list.append(f"traffic-class 7 dcb ets wrr " f"{available_bw - bw_to_assign * (len(tcs) - 1):d}")

        command_list.append("exit")
        command_list.append("exit")
        self._connection.send_command_list(command_list)

    def get_dcb_bw_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Get bandwidth of DCB traffic class from the switch port.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: traffic class bandwidth percent
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        if up > 8:
            raise ValueError(""" Mellanox switch supports up to 8 traffic classes.""")
        output = self._connection.send_command(f"show dcb ets interface ethernet {port_number} | include WRR")
        bw_info_list = any_match(output, r"\d\s+WRR\s+\d+\s+\d+")
        for bw_info in bw_info_list:
            if bw_info.strip().startswith(str(up)):
                return re.split(r"\s+", bw_info)[3]
        raise ValueError(f"Could not find Bandwidth weight on Port {port} (TC: {up})")

    def get_dcb_tc_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Retrieve traffic class by user priority for given port or dcb_map.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: assigned traffic class for user priority
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        if up > 8:
            raise ValueError("User priority has to be between 0 and 7.")
        output = self._connection.send_command(f"show dcb ets interface ethernet {port_number}")
        parsed = re.split(r"Switch\s+Priority\s+TC", output, re.I)[1]
        for prio_info in re.finditer(r"^(\s+)?\d\s+\d(\s+)?$", parsed, re.M):
            line = prio_info.group().strip()
            if str(up) == re.split(r"\s+", line)[1]:
                return line.split(" ")[0]
        raise ValueError(f"Could not find priority on Port {port} (TC: {up})")

    def get_pfc_port_statistics(self, port: str, priority: int) -> str:
        """
        Get PFC statistics for a given port.

        :param port: Mellanox switch port to configure
        :param priority: user priority (0 - 7)
        :return: pfc counter for given user priority
        :raises ValueError if parameters are invalid
        :raises SwitchException: if port statistics not found in command output
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        if priority not in list(range(8)):
            raise ValueError("Invalid priority value, must be from 0 - 7")
        output = self._connection.send_command(
            f"show int ethernet {port_number} counters pfc prio {priority:d} " f'| include "pause packets"'
        )
        result = any_match(output, r"\s*(\d+)\s*pause packets", re.I)
        if result:
            return result[0]
        else:
            raise SwitchException(f"Could not find port statistics for port {port} from pfc {output}")

    def get_port_speed(self, port: str) -> int:  # noqa W102
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        gigabit_multiplier = 1000
        output = self._connection.send_command(f"show interfaces ethernet {port_number} status")
        match = re.search(r"(?P<speed>\d+)\w", output, re.MULTILINE)
        if match:
            return int(match.group("speed")) * gigabit_multiplier
        else:
            raise SwitchException(f"Couldn't retrieve port speed for port: {port} in output: {output}")

    def set_dcb_priority_flow_control(self, priority: int, state: State) -> None:
        """
        Set DCB priority flow control.

        :param priority: Priority to set
        :param state: Status to set
        :raises ValueError if parameters are invalid
        """
        if priority not in range(8):
            raise ValueError("Invalid priority value, must be from 0 - 7")

        self._connection.send_command_list(
            [
                "configure terminal",
                f"dcb priority-flow-control priority {priority} {state.value}",
                "exit",
            ]
        )

    def enable_pfc(self) -> None:
        """Enable Priority Flow Control (PFC) on the switch."""
        commands = ["configure terminal", "dcb priority-flow-control enable force", "exit"]
        self._connection.send_command_list(commands)

    def prepare_for_pfc_on_port(self, port: str) -> None:
        """
        Prepare the port for PFC configuration.

        :param port: Port to prepare for PFC configuration
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        commands = [
            "configure terminal",
            f"interface ethernet {port_number} switchport mode hybrid",
            f"interface ethernet {port_number} switchport hybrid allowed-vlan all",
            f"interface ethernet {port_number} flowcontrol send off force",
            f"interface ethernet {port_number} flowcontrol receive off force",
            "exit",
        ]
        self._connection.send_command_list(commands)

    def enable_pfc_priority(self, priority: int) -> None:
        """
        Enable PFC for a specific priority.

        :param priority: Priority to enable
        :raises ValueError if parameters are invalid
        """
        if priority not in range(8):
            raise ValueError("Invalid priority value, must be from 0 - 7")

        self._connection.send_command_list(
            [
                "configure terminal",
                f"dcb priority-flow-control priority {priority} enable",
                "exit",
            ]
        )

    def set_ets_on_port(self, *, port: str, priority: int, mode: ETSMode, bandwidth: int | None = None) -> None:
        """
        Configure ETS on the specified port with the required configuration.

        :param port: Port to enable ETS on
        :param priority: Priority to configure (0-7)
        :param mode: Weighted Round Robin (WRR) or Strict (STRICT) mode
        :param bandwidth: In case of WRR mode, specify the bandwidth percentage for the traffic class.
                            If None, defaults to 100% for WRR mode and not applicable for STRICT mode.
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        if mode not in (ETSMode.WRR, ETSMode.STRICT):
            raise ValueError(f"Invalid ETS mode: {mode}. Must be either WRR or STRICT.")
        if mode == ETSMode.WRR and (bandwidth is None or not (0 < bandwidth <= 100)):
            raise ValueError("For WRR mode, bandwidth must be specified and between 1 and 100.")
        if priority not in range(8):
            raise ValueError("Priority must be between 0 and 7.")

        if mode == ETSMode.WRR:
            command = f"interface ethernet {port_number} traffic-class {priority} dcb ets {mode.value} {bandwidth}"
        else:
            command = f"interface ethernet {port_number} traffic-class {priority} dcb ets {mode.value}"

        commands = [
            "configure terminal",
            command,
            "exit",
        ]
        self._connection.send_command_list(commands)

    def set_bind_switch_priority_on_port(self, *, port: str, traffic_class: int, priorities: list[int]) -> None:
        """
        Bind switch priorities to the specified traffic class on the given port.

        :param port: Port to configure
        :param traffic_class: Traffic class to bind priorities to (0-7)
        :param priorities: List of switch priorities to bind to the traffic class (0-7)
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)
        if traffic_class < 0 or traffic_class > 7:
            raise ValueError("Traffic class must be between 0 and 7.")
        if not all(0 <= p <= 7 for p in priorities):
            raise ValueError("All switch priorities must be between 0 and 7.")

        commands = [
            "configure terminal",
            f"interface ethernet {port_number} traffic-class {traffic_class} "
            f"bind switch-priority {' '.join(map(str, priorities))}",
            "exit",
        ]
        self._connection.send_command_list(commands)

    def set_pfc_on_port_userspace(self, port: str) -> None:
        """
        Configure PFC on the specified port with the required configuration.

        :param port: Port to enable PFC on
        """
        self.prepare_for_pfc_on_port(port)
        self.set_bind_switch_priority_on_port(port=port, traffic_class=0, priorities=[0, 1, 2, 3, 4, 5, 6, 7])
        self.set_ets_on_port(port=port, priority=0, mode=ETSMode.WRR, bandwidth=100)
        for i in range(1, 8):
            self.set_ets_on_port(port=port, priority=i, mode=ETSMode.STRICT)

    def set_pfc_on_port_ndk(self, port: str) -> None:
        """
        Configure PFC on the specified port with the required configuration for NDK.

        :param port: Port to enable PFC on
        """
        self.prepare_for_pfc_on_port(port)
        self.set_bind_switch_priority_on_port(port=port, traffic_class=0, priorities=[0, 1, 2, 4, 5, 6, 7])
        self.set_bind_switch_priority_on_port(port=port, traffic_class=1, priorities=[3])
        self.set_ets_on_port(port=port, priority=0, mode=ETSMode.WRR, bandwidth=50)
        self.set_ets_on_port(port=port, priority=1, mode=ETSMode.WRR, bandwidth=50)
        for i in range(2, 8):
            self.set_ets_on_port(port=port, priority=i, mode=ETSMode.STRICT)
        self.set_lldp_transmit(port)
        self.set_lldp_receive(port)

    def set_lldp_transmit(self, port: str) -> None:
        """
        Enable LLDP transmit on the specified port.

        :param port: Port to enable LLDP transmit on
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        commands = [
            "configure terminal",
            f"interface ethernet {port_number} lldp transmit",
            "exit",
        ]
        self._connection.send_command_list(commands)

    def set_lldp_receive(self, port: str) -> None:
        """
        Enable LLDP receive on the specified port.

        :param port: Port to enable LLDP receive on
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        commands = [
            "configure terminal",
            f"interface ethernet {port_number} lldp receive",
            "exit",
        ]
        self._connection.send_command_list(commands)

    def disable_pfc_on_port(self, port: str) -> None:
        """
        Disable PFC on the specified port.

        :param port: Port to disable PFC on
        """
        self._validate_configure_parameters(ports=port)
        port_number = self._extract_port_number(port)

        commands = [
            f"interface ethernet {port_number} shutdown",
            f"interface ethernet {port_number} no dcb-priority-flow-control mode",
            f"interface ethernet {port_number} no shutdown",
        ]
        self._connection.send_command_list(commands)
