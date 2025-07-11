# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Class for DellOS10."""

import logging
import re
from enum import Enum
from typing import Optional, List, Dict

from mfd_common_libs import add_logging_level, log_levels

from mfd_switchmanagement.base import LLDPlink
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.utils.match import any_match
from ..dell_os9 import DellOS9

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BreakOutMode(Enum):
    """Available breakout modes."""

    ETH_400G_1x = "Eth 400g-1x"
    ETH_100G_4x = "Eth 100g-4x"
    ETH_100G_2x = "Eth 100g-2x"
    ETH_100G_1x = "Eth 100g-1x"
    ETH_40G_1x = "Eth 40g-1x"
    ETH_40G_2x = "Eth 40g-2x"
    ETH_25G_4x = "Eth 25g-4x"
    ETH_10G_4x = "Eth 10g-4x"


class DellOS10(DellOS9):
    """Class for switches with Dell OS 10."""

    PORT_REGEX = re.compile(
        r"(^((ethernet|eth|Eth)\s*(\d+/){1,2}\d+(:\d+)*)(-(\d+/){1,2}\d+(:\d+)*)*"
        r"(,(\s*(\d+/){1,2}\d+(:\d+)*)(-(\d+/){1,2}\d+(:\d+)*)*)*$)",
        re.I,
    )
    PORT_CHANNEL_REGEX = re.compile(r"^(?P<port_channel>port-channel\s\d+)$", re.I)
    MINIMUM_FRAME_SIZE = 1312
    MAXIMUM_FRAME_SIZE = 9216
    MAXIMUM_SUPPORT_TRAFFIC_CLASSES = 4

    def _convert_port_name(self, port: str) -> str:
        """
        Convert port name to switch format.

        :param port: port name
        :return: converted port name
        """
        # eth 1/1/5 -> ethernet 1/1/5
        # eth1/1/5 -> ethernet1/1/5
        port = port.strip().lower()
        if port.startswith("eth") and not port.startswith("ethernet"):
            port = port.replace("eth", "ethernet", 1)
        return port

    def _port_range(self, port: str) -> str:
        """
        Return modified command line when port range is used.

        :param port: port or port range
        :return: modified command line
        """
        return "range " if "-" in port or "," in port else ""

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Dell_os10 Switch."""
        return self.MAXIMUM_FRAME_SIZE

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command("show version")

    def _prepare_port_configuration(self, port: str) -> None:
        """
        Prepare port to configuration.

        :param port: port to configure
        """
        prange = self._port_range(port)
        port_name = f"interface {prange}{self._convert_port_name(port)}"
        self._connection.send_command_list(["configure terminal", port_name])

    def _set_ets_mode_on(self, port: str) -> None:
        """
        Set ets mode on.

        :param port: port to configure
        """
        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)
        configuration = [f"interface {prange}{self._convert_port_name(port)}", "ets mode on"]
        self._connection.send_configuration(configuration)

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure in switch range format
        :raises ValueError if parameter is invalid
        """
        self._validate_port_and_port_channel_syntax(both_syntax=ports)
        self._prepare_port_configuration(ports)
        self._connection.send_command_list(
            ["no shutdown", f"mtu {self.MAXIMUM_FRAME_SIZE}", "switchport mode access", "exit"]
        )

    def configure_vlan(self, ports: str, vlan: int, vlan_type: str, mode: str) -> None:
        """
        Configure vlan.

        Set trunking and tagging mode, create vlan if required, enable port

        :param ports: ports to configure in switch range format
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :raises ValueError if parameters are invalid
        """
        if vlan == 1:  # Unable to set ports to tagged or untagged when they're already in VLAN 1
            return None

        self._validate_configure_parameters(ports=ports, mode=mode, vlan=vlan, vlan_type=vlan_type)
        prange = self._port_range(ports)

        self._connection.send_configuration([f"interface vlan {vlan}"])
        configuration = [f"interface {prange}{self._convert_port_name(ports)}", "no shutdown"]
        if mode.lower().strip() == "access" or (
            (mode.lower().strip() == "trunk") and (vlan_type.lower().strip() == "untagged")
        ):
            configuration.append(f"switchport access vlan {vlan}")
        else:
            configuration.append("switchport mode trunk")
            configuration.append(f"switchport trunk allowed vlan {vlan}")
        self._connection.send_configuration(configuration)
        self._connection.send_configuration([f"interface vlan {vlan}", "no shutdown"])
        return None

    def _validate_ports_syntax(self, ports: str) -> None:
        self._validate_port_and_port_channel_syntax(both_syntax=ports)

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

        # get tagged ports on this VLAN
        self._connection.send_command(f"show running-configuration interface vlan {int(vlan):d}")

        self._connection.send_configuration([f"no interface vlan {vlan}"])

        # verify VLAN is completely removed
        output = self._connection.send_command(f"show running-configuration interface vlan {vlan}")
        return "error" in output.lower()

    def list_vlan_id(self) -> List[str]:
        """
        Get list of vlan id.

        :return: List of id's
        """
        output = self._connection.send_command("show running-configuration interface vlan | grep interface")
        output = [line.split(" ")[-1].strip() for line in any_match(output, r"interface\s+vlan\d+", re.I)]
        return output

    def change_standard_to_switch_mac_address(self, address: str) -> str:
        """
        Convert standard mac address to switch mac address format.

        :param address: any mac address (no separators, separated using -:., lowercase, uppercase etc.
        :return: MAC address in switch accepted format (AA:BB:CC:DD:EE:FF)
        """
        double_regex = re.compile(r"([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})")
        hex_bytes = address.lower()

        for c in ":.-":
            hex_bytes = hex_bytes.replace(c, "")

        return ":".join(double_regex.match(hex_bytes).groups())

    def get_lldp_port(self, mac: str) -> str:
        """
        Get the lldp switch port of an adapter with the specified MAC address.

        Note: For 25G Interfaces, output is re-written due to known interface lookup issue

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: switch port
        :raises SwitchException: if not found LLDP port
        """
        mac = self.change_standard_to_switch_mac_address(str(mac))

        output = self._connection.send_command(f"show lldp neighbors | grep {mac}")
        port = any_match(
            output,
            r"((ethernet|mgmt)\s*(\d+/){1,2}\d+(:\d+)*)",
            flags=re.I,
        )
        if port:
            return port[0][0]
        else:
            raise SwitchException(f"Error retrieving LLDP port for mac {mac}")

    def get_lldp_neighbors(self) -> List[LLDPlink]:
        """
        Get the lldp neighbors for switch.

        :return: list of LLDPlinks
        """
        links = []

        output = self._connection.send_command("show lldp neighbors")

        neighbor_regex = (
            r"^\s?"
            r"(?P<loc_port_id>(ethernet|mgmt)\s*(\d+/){1,2}\d+(:\d+)*)\s+"
            r"(?P<rem_host_name>\S+)\s+"
            r"(?P<rem_port_id>\S+)\s+"
            r"(?P<chassis_id>\S+)\s*$"
        )

        for match in re.finditer(neighbor_regex, output, re.MULTILINE):
            links.append(
                LLDPlink(
                    loc_portid=match.group("loc_port_id"),
                    rem_sysname=match.group("rem_host_name"),
                    rem_portid=match.group("rem_port_id"),
                    rem_devid=match.group("chassis_id"),
                )
            )
        return links

    def get_max_supported_traffic_classes(self) -> int:
        """
        Get maximum number of traffic classes that switch supports.

        :return: maximum number of traffic classes Dell switch supports (4)
        """
        return self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_port_and_port_channel_syntax(both_syntax=port)

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
                f"Invalid frame size.  Valid values are '{self.MINIMUM_FRAME_SIZE}' to '{self.MAXIMUM_FRAME_SIZE}'"
            )

        self._validate_port_and_port_channel_syntax(both_syntax=port)

        self._prepare_port_configuration(port)
        self._connection.send_command(f"mtu {frame_size}")

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
            output = self._connection.send_command(f"show mac address-table address {mac.lower()}")
            """
            Z9000-5D#show mac address-table

            Codes: pv <vlan-id> - private vlan where the mac is originally learnt
            VlanId        Mac Address         Type        Interface
            1             aa:bb:cc:dd:ee:ff   dynamic     ethernet1/1/12:1
            """
            port = any_match(
                output,
                r"(ethernet(\d+/){1,2}\d+(:\d+)*)",
                flags=re.I,
            )
            if port:
                return port[0][0]
            else:
                raise SwitchException(f"Could not find port for MAC address {mac}")
        else:
            raise SwitchException(f"Incorrect MAC address: {mac}")

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        return self._connection.send_command(f"show running-configuration interface {self._convert_port_name(port)}")

    def is_port_linkup(self, port: str) -> bool | None:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        comm = f"show interface {self._convert_port_name(port)}"
        output = self._connection.send_command(comm)
        status = rf"{port} is (?P<link_status>\w+), line protocol is (\w+)"
        matched = re.match(status, output, re.M)
        if matched:
            if matched.group("link_status") == "down":
                return False
            elif matched.group("link_status") == "up":
                return True
            return None
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")

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
            output = self._connection.send_command(f"show mac address-table address {mac.lower()}")
            """
            Z9000-5D#show mac address-table

            Codes: pv <vlan-id> - private vlan where the mac is originally learnt
            VlanId        Mac Address         Type        Interface
            1             aa:bb:cc:dd:ee:ff   dynamic     ethernet1/1/12:1
            """
            vlan = any_match(output, r"\s*(\d+)\s+\w{2}:", flags=re.I)
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
        :raises ValueError: if provided MAC address is incorrect
        """
        if self.is_mac_address(mac):
            mac = self.change_standard_to_switch_mac_address(mac)
            output = self._connection.send_command(f"show mac address-table address {mac.lower()}")
            """
            Z9000-5D#show mac address-table

            Codes: pv <vlan-id> - private vlan where the mac is originally learnt
            VlanId        Mac Address         Type        Interface
            1             3c:aa:bb:cc:41:a9   dynamic     ethernet1/1/12:1
            2             3c:aa:bb:cc:41:a9   dynamic     ethernet1/1/13:1
            """
            vlan = any_match(output, r"\s*(\d+)\s+\w{2}:", flags=re.I)
            if vlan:
                for v in vlan:
                    self._connection.send_command(f"clear mac address-table dynamic address {mac.lower()} vlan {v}")
        else:
            raise SwitchException(f"Incorrect MAC address: {mac}")

    def set_port_mirroring(self, src_port: str, dst_port: str, session: str, enabled: bool) -> None:
        """
        Set port mirroring on switch.

        :param src_port: source port name
        :param dst_port: destination port name
        :param session: session name
        :param enabled: True if Enable; False if Disable
        :raises ValueError if parameters are invalid
        """
        for port in src_port, dst_port:
            self._validate_configure_parameters(ports=port)

        if int(session) >= 65536:
            raise ValueError("Invalid Session ID. Valid Range 0 - 65535")

        if enabled:
            output = self._connection.send_command('show running-configuration | grep "monitor session"')

            if not any_match(output, session, flags=re.I):
                self._connection.send_configuration(["interface range vlan 2-4049"])
                self._connection.send_configuration(
                    [f"interface {self._convert_port_name(dst_port)}", "no mtu", "no switchport"]
                )
                self._connection.send_configuration(
                    [
                        f"monitor session {session}",
                        f"source interface {self._convert_port_name(src_port)} direction rx",
                        f"destination interface {self._convert_port_name(dst_port)}",
                    ]
                )
            else:
                raise ValueError("Session ID Requested to be Added is Already Defined!")

        else:
            output = self._connection.send_command('show running-configuration | grep "monitor session"')

            if any_match(output, session, flags=re.I):
                self._connection.send_configuration(
                    [
                        f"no monitor session {session}",
                        f"interface {dst_port}",
                        f"mtu {self.MAXIMUM_FRAME_SIZE:d}",
                        "switchport mode access",
                    ]
                )
            else:
                raise ValueError("Session ID Requested to be Removed Cannot Be Found.")

    def set_port_flowcontrol(self, port: str, rx: bool, tx: bool) -> None:
        """
        Set flowcontrol on port.

        :param port: switch port in Dell format
        :param rx: rx value to set
        :param tx: tx value to set
        """
        rx = "on" if rx else "off"
        tx = "on" if tx else "off"
        self._connection.send_configuration(
            [f"interface {self._convert_port_name(port)}", f"flowcontrol receive {rx}", f"flowcontrol transmit {tx}"]
        )

    def get_port_speed(self, port: str) -> int:  # noqa D102
        gigabit_multiplier = 1000
        output = self._connection.send_command(f"show interface {self._convert_port_name(port)}")
        match = re.search(r"LineSpeed\s+(?P<speed>\d+)G", output, re.M)
        if match:
            return int(match.group("speed")) * gigabit_multiplier
        else:
            raise SwitchException(f"Couldn't retrieve port speed for port: {port} in output: {output}")

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
                "no switchport access vlan",
                "switchport mode trunk",
                "switchport trunk allowed vlan remove 1-4093",
                f"switchport trunk allowed vlan add {vlan}",
                "no shutdown",
            ]
        )

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
                "no shutdown",
            ]
        )

    def clear_port_dcbx(self, port: str) -> None:
        """
        Clear dcbx of port.

        :param port: port to configure
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)

        configuration = [f"interface {prange}{self._convert_port_name(port)}", "no dcbx version", "no ets"]
        self._connection.send_configuration(configuration)

    def delete_port_bw_by_tc(self, port: str, suffix: str = "test") -> None:
        """
        Delete the bandwidth of traffic class on a selected port.

        :param port: switch port
        :param suffix: suffix for names
        """
        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)

        configuration = [
            f"interface {prange}{self._convert_port_name(port)}",
            f"no service-policy input type network-qos PMQ_{suffix}",
            f"no service-policy output type queuing PM_{suffix}",
            "no qos-map traffic-class",
            "no trust-map dot1p",
        ]

        self._connection.send_configuration(configuration)

    def delete_port_pfc(self, port: str) -> None:
        """
        Delete the PFC settings.

        :param port: ports
        """
        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)

        configuration = [f"interface {prange}{self._convert_port_name(port)}", "no priority-flow-control"]
        self._connection.send_configuration(configuration)

    def delete_qos_policy(self, suffix: str = "test") -> None:
        """
        Delete the policy for QOS.

        :param suffix: to use in names
        """
        configuration = [
            f"no policy-map type queuing PM_{suffix}",
            f"no class-map type queuing Q7_{suffix}",
            f"no class-map type queuing Q6_{suffix}",
            f"no class-map type queuing Q5_{suffix}",
            f"no class-map type queuing Q4_{suffix}",
            f"no class-map type queuing Q3_{suffix}",
            f"no class-map type queuing Q2_{suffix}",
            f"no class-map type queuing Q1_{suffix}",
            f"no class-map type queuing Q0_{suffix}",
            f"no qos-map traffic-class QM_{suffix}",
            f"no trust dot1p-map TM_{suffix}",
            f"no policy-map type network-qos PMQ_{suffix}",
            f"no class-map type network-qos CMQ_{suffix}",
        ]
        self._connection.send_configuration(configuration)

    def create_qos_policy(self, bandwidth: List[int], up2tc: List[int], suffix: str = "test") -> None:
        """
        Create QOS policy.

        :param bandwidth: list of bandwidth per traffic class
        :param up2tc: list of assignment of QoS priority to traffic class
        :param suffix: suffix to use in names
        """
        trust_commands = [f"trust dot1p-map TM_{suffix}"]
        policy_map_dict = {}
        priority = 8
        indexes = []
        for i in range(priority):  # there are 3 bits for priority so 8 values
            if i in up2tc:
                indexes.append(i)
                cos_value = ",".join([str(qos_prio) for qos_prio, tc in enumerate(up2tc) if tc == i])

                trust_commands.append(f"qos-group {i} dot1p {cos_value}")
                policy_map_dict[f"Q{i}_{suffix}"] = bandwidth[i]
        trust_commands.append("exit")

        self._connection.send_configuration(trust_commands)
        self.create_qos_map(queues=indexes, tc_name=f"QM_{suffix}", queue_type="ucast")
        self.create_qos_map(queues=indexes, tc_name=f"QM_{suffix}", queue_type="mcast")
        for i in indexes:
            self.create_qos_class_map(name=f"Q{i}_{suffix}", priority=str(i), class_type="queuing")

        self.create_qos_queuing_policy_map(f"PM_{suffix}", policy_map_dict)

        cos_value_list = [str(qos_prio) for qos_prio, tc in enumerate(up2tc) if tc > 0]
        cos_value = ",".join(cos_value_list)
        class_names = [f"CMQ_{suffix}" for _ in range(len(cos_value))]
        self.create_qos_class_map(name=f"CMQ_{suffix}", priority=cos_value, class_type="network-qos")
        self.create_network_qos_policy_map(name=f"PMQ_{suffix}", class_names=class_names, cos_values=cos_value_list)

    def create_qos_map(self, queues: List[int], tc_name: str, queue_type: str) -> None:
        """
        Create QoS map.

        :param queues: list of queues which should be created
        :param tc_name: name of created traffic class
        :param queue_type: ucast | mcast
        """
        qos_map_commands = [f"qos-map traffic-class {tc_name}"]
        for i in set(queues):
            qos_map_commands.append(f"queue {i} qos-group {i} type {queue_type}")
        self._connection.send_configuration(qos_map_commands)

    def create_qos_queuing_policy_map(self, name: str, class_bandwidth_dict: Dict[str, int]) -> None:
        """
        Create QoS queuing policy map from dictionary with bandwidth values.

        :param name: Name of desired policy
        :param class_bandwidth_dict: Dict with bandwidth values for each class
        :raises ValueError if bandwidths do not sum up to 100%
        """
        if sum(class_bandwidth_dict.values()) != 100:
            raise ValueError("Bandwidths do not sum to 100%!")

        qos_queuing_map_commands = [f"policy-map type queuing {name}"]
        for class_map, bandwidth_percentage in class_bandwidth_dict.items():
            qos_queuing_map_commands.append(f"class {class_map}")
            qos_queuing_map_commands.append(f"bandwidth percent {bandwidth_percentage}")
            qos_queuing_map_commands.append("exit")

        self._connection.send_configuration(qos_queuing_map_commands)

    def create_qos_class_map(self, name: str, priority: str, class_type: str = "network-qos") -> None:
        """
        Create QoS class map.

        :param name: name of class map
        :param priority: qos-group priority value, if it's list, should be separated by ","
        :param class_type: class type, e.g.network-qos, queuing
        :raises SwitchException if priority or class_type are incorrect
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Create QoS class map: {name}, type: {class_type}, priority: {priority}.",
        )
        pattern = r"(\d+),?"
        if not re.match(pattern=pattern, string=priority):
            raise SwitchException(f"Priority format is incorrect: {priority}")

        class_types = ["network-qos", "queuing"]
        if class_type not in class_types:
            raise SwitchException(f"Not supported class_typed used: {class_type}, accepted: {class_types}")
        match_call = "qos-group" if class_type == "network-qos" else "queue"

        commands_list = [f"class-map type {class_type} {name}", f"match {match_call} {priority}"]
        self._connection.send_configuration(commands_list)

    def create_network_qos_policy_map(self, name: str, class_names: List[str], cos_values: List[str]) -> None:
        """
        Create network QoS policy map.

        :param name: Name of the network policy map
        :param class_names: List with names of classes for each CoS value
        :param cos_values: List with CoS values
        """
        if len(class_names) != len(cos_values):
            raise SwitchException("Lengths of class_names and cos_values should be the same!")

        configuration = [f"policy-map type network-qos {name}"]
        for cos_value, class_name in zip(cos_values, class_names):
            configuration.append(f"class {class_name}")
            configuration.append("pause")
            configuration.append(f"pfc-cos {cos_value}")
            configuration.append("exit")

        self._connection.send_configuration(configuration)

    def set_port_bw_by_tc(self, port: str, bandwidth: List[int] = None, suffix: str = "test") -> None:
        """
        Set the bandwidth of traffic class on a selected port.

        :param port: switch port
        :param bandwidth: list of bandwidth (not used)
        :param suffix: suffix for names
        """
        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)

        configuration = [
            f"interface {prange}{self._convert_port_name(port)}",
            f"trust-map dot1p TM_{suffix}",
            f"qos-map traffic-class QM_{suffix}",
            f"service-policy output type queuing PM_{suffix}",
            f"service-policy input type network-qos PMQ_{suffix}",
        ]
        self._connection.send_configuration(configuration)

    def set_port_pfc_by_tc(self, port: str, qos_priority: Optional[int], pfc: str) -> None:
        """
        Configure PFC settings.

        :param port: port
        :param qos_priority: QoS priority (0 ~ 7)
        :param pfc: PFC state
        :raises ValueError if parameters are invalid
        """
        if pfc == "off":
            return self.delete_port_pfc(port)

        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)

        configuration = [
            f"interface {prange}{self._convert_port_name(port)}",
            "flowcontrol receive off",
            "flowcontrol transmit off",
            "priority-flow-control mode on",
        ]
        self._connection.send_configuration(configuration)

    def show_port_dcbx(self, port: str) -> str:
        """
        Show dcbx configuration including peer info.

        :param port: port (no range)
        :raises ValueError if parameters are invalid
        """
        port = port.split("-")[0]
        port = port.split(",")[0]
        self._validate_configure_parameters(ports=port)
        output = self._connection.send_command(f"show lldp dcbx interface {self._convert_port_name(port)}")
        return output

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set the DCBX version for the switch port.

        :param port: port
        :param mode: DCBX mode
        :raises ValueError if parameters are invalid
        """
        mode = mode.lower()
        if mode not in {"cee", "ieee"}:
            raise ValueError("Invalid DCBX value, must be either 'CEE' or 'IEEE'")

        self._validate_configure_parameters(ports=port)
        prange = self._port_range(port)
        self._set_ets_mode_on(port)
        configuration = [f"interface {prange}{self._convert_port_name(port)}", f"dcbx version {mode}"]
        self._connection.send_configuration(configuration)

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(both_syntax=port)
        if shutdown:
            self.disable_port(port, 1)
        else:
            self.enable_port(port, 1)

    @staticmethod
    def _validate_port_channel_no(pc_no: int) -> None:
        """Validate port channel number.

        :param pc_no: number of port channel
        :raises: ValueError if port-channel number is out of accepted range.
        """
        if pc_no not in range(1, 129):
            raise ValueError("Port channel interface number should be integer in range 1-128")

    def create_port_channel_interface(self, pc_no: int) -> None:
        """Create port channel interface with given number.

        :param pc_no: number of port channel
        """
        self._validate_port_channel_no(pc_no)
        commands = ["configure terminal", f"interface port-channel {pc_no}"]
        self._connection.send_command_list(commands)

    def set_switchport_mode(self, port: str, mode: str) -> None:
        """Set switchport mode.

        :param port: port of switch
        :param mode: switchport mode
        :raises ValueError when switchport mode is incorrect
        """
        self._validate_port_and_port_channel_syntax(both_syntax=port)
        if mode not in ["access", "trunk"]:
            raise ValueError("Incorrect switchport mode")

        commands = ["configure terminal", f"interface {self._convert_port_name(port)}", f"switchport mode {mode}"]
        self._connection.send_command_list(commands)

    def add_port_to_channel_group(
        self, port: str, pc_no: int, *, mode: Optional[str] = None, **kwargs: Optional[str]
    ) -> None:
        """Add ethernet port to port channel group.

        :param port: port of switch
        :param pc_no: number of port channel interface
        :param mode : LACP mode
        :kwargs: Other parameters
        :raises ValueError when mode is incorrect
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        self._validate_port_channel_no(pc_no)
        allowed_mode_values = ["active", "on", "passive"]
        commands = ["configure terminal", f"interface {self._convert_port_name(port)}", f"channel-group {pc_no}"]

        if mode:
            if mode not in allowed_mode_values:
                raise ValueError(f"{mode} is incorrect parameter for channel-group mode")
            commands[2] += f" mode {mode}"

        self._connection.send_command_list(commands)

    def set_lacp_rate(self, port: str, lacp_rate: str) -> None:
        """Set LACP rate on ethernet port.

        :param port: port of switch
        :param lacp_rate: rate of lacp frames
        :raises ValueError when rate is incorrect
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        allowed_values = ["fast", "normal"]
        if lacp_rate not in allowed_values:
            raise ValueError(f"{lacp_rate} is incorrect option for LACP rate")

        commands = ["configure terminal", f"interface {self._convert_port_name(port)}", f"lacp rate {lacp_rate}"]
        self._connection.send_command_list(commands)

    def disable_lacp_rate(self, port: str, lacp_rate: str) -> None:
        """Disable LACP rate on port.

        :param port: port of switch:
        :param lacp_rate: rate of lacp frames
        """
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        allowed_values = ["fast", "normal"]
        if lacp_rate not in allowed_values:
            raise ValueError(f"{lacp_rate} is incorrect option for LACP rate")

        commands = ["configure terminal", f"interface {self._convert_port_name(port)}", f"no lacp rate {lacp_rate}"]
        self._connection.send_command_list(commands)

    def remove_port(self, port: str) -> None:
        """Remove port from switch.

        :param port: port of switch
        """
        self._validate_port_and_port_channel_syntax(port_channel=port)
        commands = ["configure terminal", f"no interface {self._convert_port_name(port)}"]
        self._connection.send_command_list(commands)

    def configure_qos_pfc_interface(
        self,
        *,
        port: str,
        qos_policy: str,
        traffic_policy: str,
        trust_policy: str,
        service_policy: str,
    ) -> None:
        """
        Configure QoS PFC interface.

        :param port: port to configure
        :param qos_policy: QoS policy
        :param traffic_policy: traffic policy
        :param trust_policy: trust policy
        :param service_policy: service policy
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Configure QoS PFC interface.")
        self._validate_port_and_port_channel_syntax(ethernet_port=port)
        conf_commands_part_one = [
            f"interface {self._convert_port_name(port)}",
            f"service-policy output type queuing {qos_policy}",
            f"qos-map traffic-class {traffic_policy}",
            f"trust-map dot1p {trust_policy}",
            "flowcontrol transmit off",
            "flowcontrol receive off",
            f"service-policy input type network-qos {service_policy}",
        ]

        conf_commands_part_two = [
            f"interface {self._convert_port_name(port)}",
            "priority-flow-control mode on",
            "lldp tlv-select dcbxp-appln iscsi",
        ]

        self._connection.send_configuration(conf_commands_part_one)
        self._set_ets_mode_on(port)
        self._connection.send_configuration(conf_commands_part_two)

    def create_iscsi_policy_map(self, name: str) -> None:
        """
        Create iSCSI policy map.

        :param name: QoS policy map name
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Create iSCSI policy map: {name}")
        commands = [
            f"policy-map type application {name}",
            "class class-iscsi",
            "set qos-group 4",
            "set cos 4",
            "exit",
        ]
        self._connection.send_configuration(commands)

    def get_port_groups(self) -> Dict[str, List[str]]:
        """
        Get port groups from the switch together with belonging ports.

        :return: dict with port groups names as keys and lists of belonging ports as values
        """
        output = self._connection.send_command("show port-group")
        port_group_regex = (
            r"port-group(\d+/\d+/\d+)\s*unrestricted\s*<?((?:\s*(?:\d+/\d+/\d+)\s*(?:Disabled|Eth\s\d+g-\dx)\n?)+)"
        )
        port_groups = re.findall(port_group_regex, output, re.M)

        ports_in_group = dict()
        ports_regex = r"\d+/\d+/\d+"
        for group, ports in port_groups:
            port_list = re.findall(ports_regex, ports, re.M)
            ports_in_group[group] = port_list

        return ports_in_group

    def set_port_group_mode(self, port_group: str, mode: BreakOutMode, *, port: Optional[str] = None) -> None:
        """
        Set mode for group of ports or single port in group.

        :param port_group: name of group of ports
        :param mode: mode to be set
        :param port: if specified, mode will be set for this specific port only
        """
        commands = [f"port-group {port_group}"]
        port_command = f"port {self._convert_port_name(port)} " if port is not None else ""
        commands.append(port_command + f"mode {mode.value}")
        self._connection.send_configuration(commands)

    def show_lldp_info(self, port: str) -> str:
        """
        Verify the LLDP neighbor info on switch.

        :param port: port of switch
        :return: Output of the command
        """
        return self._connection.send_command(f"show lldp neighbors interface {self._convert_port_name(port)} detail")

    def configure_lldp(self, port: str, param: str) -> str:
        """
        Configure LLDP on switch.

        :param port: port of switch
        :param param: Parameter to receive or transmit
        :raises: ValueError if parameters are incorrect
        """
        if param not in ["receive", "transmit"]:
            raise ValueError(f"Invalid parameter: {param}. Valid values are 'receive' or 'transmit'.")
        else:
            return self._connection.send_configuration(
                [
                    f"interface {self._convert_port_name(port)}",
                    f"lldp {param}",
                ]
            )
