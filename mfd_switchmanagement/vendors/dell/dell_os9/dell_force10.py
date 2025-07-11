# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dell Force 10."""

import re
from typing import List, Tuple

from .base import DellOS9
from mfd_switchmanagement.base import LLDPlink
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.utils.match import any_match


class DellOS9_Force10(DellOS9):
    """Class for Dell Force10."""

    PORT_REGEX = re.compile(
        r"(^((gi|te|fo|tw|tf|fi|hu) ?(\d+/){1,2}\d+)( - (\d+/)*\d+)?( , "
        r"((gi|te|fo|tw|tf|fi|hu) ?(\d+/){1,2}\d+)(-(\d+/)*\d+)?)*$|^po\d+$)",
        re.I,
    )
    MINIMUM_FRAME_SIZE = 594
    MAXIMUM_FRAME_SIZE = 12000
    MAXIMUM_SUPPORT_TRAFFIC_CLASSES = 4

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
            self._connection.send_command("clear mac-address-table dynamic address " + mac.upper())
        else:
            raise SwitchException(f"Incorrect MAC address: {mac}")

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)
        self._prepare_port_configuration(ports)
        self._connection.send_command_list(["no shutdown", f"mtu {self.MAXIMUM_FRAME_SIZE}", "switchport", "exit"])
        ports = ports.replace(" ", "")
        self._connection.send_command_list(
            [
                "interface range vlan 2 - 4049",
                f"no untagged {ports}",
                f"no tagged {ports}",
                "end",
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
        if vlan == 1:  # Unable to set ports to tagged or untagged when they're already in VLAN 1 on Force10
            return None
        self._validate_configure_parameters(ports, mode, vlan, vlan_type)

        prange = ""
        if "-" in ports or "," in ports:
            prange = "range "

        self._connection.send_configuration([f"interface  {prange}{ports}", "no shutdown", "switchport"])
        ports = ports.replace(" ", "")
        configuration = [f"interface vlan {vlan}"]
        if mode.lower().strip() == "access" or (
            (mode.lower().strip() == "trunk") and (vlan_type.lower().strip() == "untagged")
        ):
            configuration.append(f"untagged {ports}")
        else:
            configuration.append(f"tagged {ports}")
        configuration.append("no shutdown")
        self._connection.send_configuration(configuration)

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
        output = self._connection.send_command(f"show running-config interface vlan {int(vlan):d}")
        tagged_ports = any_match(output, r"tagged\s+[\w\d /,-]+", re.I)

        # remove tagged ports
        config_list = [f"interface vlan {vlan}"]
        for tagged in tagged_ports:
            config_list.append(f"no {tagged}")
        config_list.append(["shutdown"])
        self._connection.send_configuration(config_list)
        self._connection.send_configuration([f"no interface vlan {vlan}"])

        # verify VLAN is completely removed
        output = self._connection.send_command(f"show running-config interface vlan {vlan}")
        return "error" in output.lower()

    def list_vlan_id(self) -> List[str]:
        """
        Get list of vlan id.

        :return: List of id's
        """
        output = self._connection.send_command("show running-config interface vlan | grep interface")
        output = [line.split(" ")[-1].strip() for line in any_match(output, r"interface\s+vlan\s+\d+", re.I)]
        return output

    def change_standard_to_switch_mac_address(self, address: str) -> str:
        """
        Convert standard mac address to switch mac address format.

        :param address: any mac address (no separators, separated using -:., lowecase, uppercase etc.
        :return: MAC address in switch accepted format (AA:BB:CC:DD:EE:FF)
        """
        double_regex = re.compile(r"([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})")
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
            output = self._connection.send_command(f"sh mac-address-table address {mac.upper()}")
            port = any_match(
                output,
                r"(([g|G]i|[t|T][e|f]|[f|F]o|[f|F]i|[h|H]u) (\d+/){1,2}\d+)",
                flags=re.I,
            )
            if port:
                return port[0][0].replace("Tf", "Tw", 1)
            else:
                raise SwitchException(f"Could not find port for MAC address {mac}")
        else:
            raise SwitchException(f"Incorrect MAC address: {mac}")

    def get_lldp_port(self, mac: str, san: str = "") -> str:
        """
        Get the lldp switch port of an adapter with the specified MAC address.

        Note: For 25G Interfaces, output is re-written due to known interface lookup issue

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :param san: standard switch address
        :return: switch port
        """
        mac = self.change_standard_to_switch_mac_address(str(mac))

        output = self._connection.send_command(f"sh lldp neighbors | grep {mac}")
        port = any_match(
            output,
            r"(([g|G]i|[t|T][e|f]|[f|F]o|[f|F]i|[h|H]u) (\d+/){1,2}\d+)",
            flags=re.I,
        )
        if port:
            return port[0][0].replace("Tf", "Tw", 1)
        else:
            san = self.change_standard_to_switch_mac_address(str(san))
            output = self._connection.send_command(f"sh lldp neighbors |grep {san}")
            port = any_match(
                output,
                r"(([g|G]i|[t|T][e|f]|[f|F]o|[f|F]i|[h|H]u) (\d+/){1,2}\d+)",
                flags=re.I,
            )
            if port:
                return port[0][0].replace("Tf", "Tw", 1)
            else:
                raise SwitchException(f"Error retrieving LLDP port for mac {mac}")

    def get_lldp_neighbors(self) -> List[LLDPlink]:
        """
        Get the lldp neighbors for switch.

        :return: list of LLDPlinks
        """
        links = []

        output = self._connection.send_command("do show lldp neighbors")

        neighbor_regex = (
            r"^\s?"
            r"(?P<loc_port_id>[a-zA-Z]{2}\s+(\d+|\/){2}\d+)\s+"
            r"(?P<rem_host_name>\S+)\s+"
            r"(?P<rem_port_id>\S+)\s+"
            r"(?P<chassis_id>\S+)\s+$"
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

    def get_port_dcbx_version(self, port: str) -> str:
        """
        Get dcbx version of port.

        :param port: port to check
        :return: dcbx version
                :raises ValueError if parameters are invalid

        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"sh run int {port} | grep dcbx")
        dcbx = any_match(output, r"(\bcee|\bieee)", flags=re.I)
        if dcbx:
            return dcbx[0]
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
        prange = ""
        if "all" in port or "-" in port or "," in port:
            prange = "range "

        dcbx = any_match(mode, r"(\bCEE|\bIEEE)", flags=re.I)
        if not dcbx:
            raise ValueError("Invalid DCBX value, must be either 'CEE' or 'IEEE'")

        self._connection.send_configuration([f"interface {prange}{port}", "protocol lldp", f"dcbx version {mode}"])

    def get_max_supported_traffic_classes(self) -> int:
        """
        Get maximum number of traffic classes that switch supports.

        :return: maximum number of traffic classes Dell switch supports (4)
        """
        return self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES

    def set_default_dcb_config(self, port: str, dcbmap: str) -> None:
        """
        Set a default DCB configuration to the switch port.

        For Dell switch, this function will create a DCB map with 3 Priority groups as
        * Priority group 0: 10% bandwidth, PFC off (User priorities: 0, 1, 2, 5, 6, 7)
        * Priority group 1: 10% bandwidth, PFC off (User priorities: 3)
        * Priority group 2: 80% bandwidth, PFC off (User priorities: 4)

        :param port: switch port in Dell format
        :param dcbmap: name of DCB map to store DCB configuration
        """
        # check this DCB map is duplicated
        same_dcbmap_exists = False
        output = self._connection.send_command(f"show running-config dcb-map | grep {dcbmap}")
        if any_match(output, dcbmap, flags=re.I):
            config_list = [f"dcb-map {dcbmap}", "show config"]
            output = self._connection.send_configuration(config_list)
            same_dcbmap_exists = (
                any_match(output, "priority-group 0 bandwidth 10 pfc off", re.I)
                and any_match(output, "priority-group 1 bandwidth 10 pfc off", re.I)
                and any_match(output, "priority-group 2 bandwidth 80 pfc off", re.I)
                and any_match(output, "priority-pgid 0 0 0 1 2 0 0 0", re.I)
            )

        if not same_dcbmap_exists:
            self.set_dcb_map_tc(dcbmap, 0, 10, "off")
            self.set_dcb_map_tc(dcbmap, 1, 10, "off")
            self.set_dcb_map_tc(dcbmap, 2, 80, "off")
            self.set_dcb_map_up(dcbmap, "0 0 0 1 2 0 0 0")

        self.set_port_dcb_map(port, dcbmap)

    def set_default_ets_config(self, port: str, dcbmap: str) -> None:
        """
        Set a default ETS configuration to the switch port.

        For Dell switch, this function will create a DCB map with 4 Priority groups as
        * Priority group 0: 10% bandwidth, PFC off (User priorities: 0, 1, 2)
        * Priority group 1: 30% bandwidth, PFC off (User priorities: 3)
        * Priority group 2: 40% bandwidth, PFC off (User priorities: 4)
        * Priority group 3: 20% bandwidth, PFC off (User priorities: 5, 6, 7)

        :param port: switch port in Dell format
        :param dcbmap: name of DCB map to store DCB configuration
        """
        # check this DCB map is duplicated
        same_dcbmap_exists = False
        output = self._connection.send_command(f"show running-config dcb-map | grep {dcbmap}")
        if any_match(output, dcbmap, flags=re.I):
            config_list = [f"dcb-map {dcbmap}", "show config"]
            output = self._connection.send_configuration(config_list)
            same_dcbmap_exists = (
                any_match(output, "priority-group 0 bandwidth 10 pfc off", re.I)
                and any_match(output, "priority-group 1 bandwidth 30 pfc off", re.I)
                and any_match(output, "priority-group 2 bandwidth 40 pfc off", re.I)
                and any_match(output, "priority-group 3 bandwidth 20 pfc off", re.I)
                and any_match(output, "priority-pgid 0 0 0 1 2 3 3 3", re.I)
            )

        if not same_dcbmap_exists:
            self.set_dcb_map_tc(dcbmap, 0, 10, "off")
            self.set_dcb_map_tc(dcbmap, 1, 30, "off")
            self.set_dcb_map_tc(dcbmap, 2, 40, "off")
            self.set_dcb_map_tc(dcbmap, 3, 20, "off")
            self.set_dcb_map_up(dcbmap, "0 0 0 1 2 3 3 3")

        self.set_port_dcb_map(port, dcbmap)

    def get_port_dcb_map(self, port: str) -> str:
        """
        Get the DCB MAP name applied to a given switch port.

        :param port: switch port
        :return: DCB MAP name
        :raises SwitchException on failure
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"sh run int {port} | grep dcb-map")
        dcbmap = any_match(output, r"(dcb-map)\s(\w+)", flags=re.I)
        if dcbmap:
            return dcbmap[0][1]
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
        prange = ""
        if "all" in port or "-" in port or "," in port:
            prange = "range "

        # remove if there is a dcb map previously assigned
        output = self._connection.send_command(f"show running-config interface {port} | grep dcb-map")
        prev_dcbmap = any_match(output, r"dcb-map\s+\w+", flags=re.I)
        if len(prev_dcbmap) != 0:
            self._connection.send_configuration(
                [f"interface {prange}{port}", f"no dcb-map {prev_dcbmap[0].split()[1]}"]
            )
        self._connection.send_configuration([f"interface {prange}{port}", f"dcb-map {dcbmap}"])

    def set_dcb_map_tc(self, dcbmap: str, tc: int, bw: int, pfc: str) -> None:
        """
        Configure a DCB MAP with TC, BW and PFC settings.

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

        if tc not in list(range(self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES)):
            raise ValueError(f"Invalid TC value, must be between 0-{self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES - 1} range")

        self._connection.send_configuration([f"dcb-map {dcbmap}", f"priority-group {tc} bandwidth {bw} pfc {pfc}"])

    def get_dcb_map_up(self, dcbmap: str) -> str:
        """
        Get user priority group for DCB Map.

        :param dcbmap: map to check.
        :return: user priority group
        :raises SwitchException on failure
        """
        # priority-pgid 0 0 0 1 2 3 3 3
        output = self._connection.send_configuration([f"dcb-map {dcbmap}", "show config"])

        pgid_group = any_match(output, r"((([0-7])\s){7}([0-7]))", flags=re.I)
        if not pgid_group:
            raise SwitchException(f"Error retrieving user priority group for DCB Map {dcbmap}")
        else:
            return pgid_group[0][0]

    def set_dcb_map_up(self, dcbmap: str, up: str) -> None:
        """
        Set a User Priority Group on a DCB MAP.

        :param dcbmap: DCB-MAP name
        :param up: User Priority Group
        :raises ValueError if parameters are invalid
        """
        """
        stwn-u28-s5000(conf-dcbmap-Felix)#priority-pgid 0 0 0 1 1 1 1 1

        Set priorities 0-2 in TC 0, 3-7 in TC 1
        """
        pattern = any_match(up, r"((([0-7])\s){6}([0-7]))", flags=re.I)
        if not pattern:
            raise ValueError("Invalid priority-pgid format")

        self._connection.send_configuration([f"dcb-map {dcbmap}", f"priority-pgid {up}"])

    def delete_dcb_map(self, port: str, dcbmap: str) -> None:
        """
        Delete a given DCB-MAP from the switch port and switch config.

        :param port: port of switch
        :param dcbmap: DCB-MAP name
        """
        self._connection.send_configuration([f"interface {port}", f"no dcb-map {dcbmap}"])
        self._connection.send_configuration([f"no dcb-map {dcbmap}"])

    def get_dcb_map_bw_by_tc(self, dcbmap: str, tc: int) -> str:
        """
        Get the bandwidth percentage of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :return: Bandwidth value
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if tc >= self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(f"Dell switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES} traffic classes.")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap} | grep PG:{tc}")
        bw = any_match(output, rf"((PG:{tc:d})\s*(TSA:ETS)\s*(BW:(\d+)))", flags=re.I)
        if bw:
            return bw[0][4]
        else:
            raise SwitchException(f"Error retrieving bandwidth percentage for DCB-MAP {dcbmap}, PG {tc}")

    def get_dcb_map_pfc_by_tc(self, dcbmap: str, tc: int) -> str:
        """
        Get the PFC state of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: int Traffic Class
        :return: PFC state
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if tc not in list(range(7)):
            raise ValueError("Invalid TC value, must be between 0-7 range")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap} | grep PG:{tc}")
        pfc = any_match(output, rf"((PG:{tc:d})\s*(TSA:ETS)\s*(BW:(\d+))\s*(PFC:(\w+)))", flags=re.I)
        if pfc:
            return pfc[0][6]
        else:
            raise SwitchException(f"Error retrieving PFC state for DCB-MAP {dcbmap}, TC {tc}")

    def get_dcb_map_pfc(self, dcbmap: str) -> str:
        """
        Get the global PFC state for a given DCB MAP.

        :param dcbmap: DCB-MAP name
        :return: PFC state
        :raises SwitchException on failure
        """
        output = self._connection.send_command(f"sh qos dcb-map {dcbmap} | grep PfcMode")
        pfc = any_match(output, r"((ON|OFF))", flags=re.I)
        if pfc:
            return pfc[0][1]
        else:
            raise SwitchException(f"Error retrieving PFC state for DCB-MAP {dcbmap}")

    def set_dcb_qos_conf(self, port: str, dcbmap: str, dcb_tc_info_list: [(str, str, str)]) -> None:
        """
        Configure DCB traffic on the switch port.

        :param port: port of switch
        :param dcbmap: switch DCB map name to assign
        :param dcb_tc_info_list: DCB traffic class info list.
        length of list has to be 3 or less (str traffic_class, str bandwidth, str pfc='off')
        :raises ValueError if parameters are invalid
        """
        if len(dcb_tc_info_list) > self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES - 1:
            raise ValueError(f"Dell switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:d} traffic classes.")

        available_bw = 100
        current_pg = 1
        pgid_list = [0, 0, 0, 0, 0, 0, 0, 0]
        for info in dcb_tc_info_list:
            self.set_dcb_map_tc(dcbmap, current_pg, int(info[1]), info[2])
            pgid_list[int(info[0])] = current_pg
            available_bw -= int(info[1])
            current_pg += 1
        if available_bw <= 0 and 0 in pgid_list:
            raise ValueError("Total bandwidth cannot be exceed 100%.")
        self.set_dcb_map_tc(dcbmap, 0, available_bw, "off")
        self.set_dcb_map_up(dcbmap, " ".join(str(pg) for pg in pgid_list))
        self.set_port_dcb_map(port, dcbmap)

    def get_dcb_tc_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Retrieve traffic class by user priority for given port or dcb_map.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: assigned traffic class for user priority
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if up not in list(range(8)):
            raise ValueError("User priority has to be between 0 and 7.")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap}")
        for pg_info in output.split("PG:"):
            result = re.search(rf"Priorities:([0-7]\s+)*{up:d}([0-7]\s+)*", pg_info, re.I)
            if result:
                return pg_info[0]
        raise SwitchException(f" Could not find priority information (UP:{up:d}) from DCB MAP {dcbmap}")

    def get_dcb_bw_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Get bandwidth of DCB traffic class from the switch port.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: traffic class bandwidth percent
        """
        return str(self.get_dcb_map_bw_by_tc(dcbmap, int(self.get_dcb_tc_by_up(port, dcbmap, up))))

    def get_pfc_port_statistics(self, port: str, priority: int) -> str:
        """
        Get PFC statistics for a given port.

        :param port: Dell switch port to configure
        :param priority: user priority (0 - 7)
        :return: pfc counter for given user priority
        :raises ValueError if parameters are invalid
        :raises SwitchException: if port statistics not found in command output
        """
        if priority not in list(range(8)):
            raise ValueError("Invalid priority value, must be from 0 - 7")

        output = self._connection.send_command(f"sh int {port} pfc statistics | grep P{priority:d}")
        result = any_match(output, rf"{port[2:]}\s*P{priority:d}\s*(\d+)", re.I)
        if result:
            return result[0]
        else:
            raise SwitchException(f"Could not find port statistics for port {port} from pfc {output}")

    def get_dcb_tc_bw(self, dcbmap: str, tc: int) -> str:
        """
        Get bandwidth of DCB traffic class.

        :param dcbmap: str DCB-MAP name
        :param tc: traffic class
        :return: Bandwidth value
        """
        return self.get_dcb_map_tc_bw(dcbmap, int(self.get_dcb_tc_pg(dcbmap, tc)))

    def get_dcb_map_tc_bw(self, dcbmap: str, pg: int) -> str:
        """
        Get the bandwidth percentage of Priority Group in DCB MAP.

        :param dcbmap: str DCB-MAP name
        :param pg: Priority Group
        :return: Bandwidth value
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if pg not in list(range(4)):
            raise ValueError("Invalid priority group value, must be between 0-3 range")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap} | grep PG:{pg:d}")
        bw = any_match(output, rf"((PG:{pg:d})\s*(TSA:ETS)\s*(BW:(\d+)))", flags=re.I)
        if bw:
            return bw[0][4]
        else:
            raise SwitchException(f"Error retrieving bandwidth percentage for DCB-MAP {dcbmap}, PG {pg}")

    def get_dcb_tc_pg(self, dcbmap: str, tc: int) -> str:
        """
        Return priority group of DCB traffic class from the switch port.

        :param dcbmap: Dell switch DCB map name to assign (will not be used in Mellanox switch)
        :param tc: traffic class (0 ~ 7)
        :return: traffic class priority group
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if tc not in list(range(8)):
            raise ValueError("Dell switch supports up to 8 traffic classes.")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap}")
        for pg_info in output.split("PG:"):
            result = re.search(rf"Priorities:([0-7]\s+)*{tc:d}([0-7]\s+)*", pg_info, re.I)
            if result is not None:
                return pg_info[0]
        raise SwitchException(f" Could not find priority information (TC:{dcbmap:d}) from DCB MAP {str(tc)}")

    def set_dcb_tc(self, port: str, dcbmap: str, dcb_tc_info_list: List[Tuple[str, str, str]]) -> None:
        """
        Configure DCB traffic on the switch port.

        :param port: Dell switch port to configure
        :param dcbmap: Dell switch DCB map name to assign
        :param dcb_tc_info_list: DCB traffic class info list. (str traffic_class, str bandwidth, str pfc='off')
        :raises ValueError if parameters are invalid
        """
        if len(dcb_tc_info_list) > 3:
            raise ValueError("Dell switch supports up to 4 priority groups.")

        available_bw = 100
        current_pg = 1
        pgid_list = [0, 0, 0, 0, 0, 0, 0, 0]
        for info in dcb_tc_info_list:
            bandwidth = int(info[1])
            self.set_dcb_map_tc(dcbmap, current_pg, bandwidth, info[2])
            pgid_list[int(info[0])] = current_pg
            available_bw -= bandwidth
            current_pg += 1
        if available_bw <= 0 and 0 in pgid_list:
            raise ValueError("Total bandwidth cannot be exceed 100%.")
        self.set_dcb_map_tc(dcbmap, 0, available_bw, "off")
        self.set_dcb_map_up(dcbmap, " ".join(str(pg) for pg in pgid_list))
        self.set_port_dcb_map(port, dcbmap)

    def get_dcb_map_tc_pfc(self, dcbmap: str, tc: int) -> str:
        """
        Get the PFC state for a Traffic Class and DCB MAP.

        :param dcbmap: str DCB-MAP name
        :param tc: int Traffic Class
        :return: str PFC state
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if tc not in list(range(8)):
            raise ValueError("Invalid TC value, must be between 0-7 range")

        output = self._connection.send_command(f"sh qos dcb-map {dcbmap} | grep PG:{tc:d}")
        pfc = any_match(output, rf"((PG:{tc:d})\s*(TSA:ETS)\s*(BW:(\d+))\s*(PFC:(\w+)))", flags=re.I)
        if pfc:
            return pfc[0][6]
        else:
            raise SwitchException(f"Error retrieving PFC state for DCB-MAP {dcbmap}, TC {tc}")

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
            output = self._connection.send_command('show running-config | grep "monitor session"')

            if not any_match(output, session, flags=re.I):
                self._connection.send_configuration(
                    ["interface range vlan 2 - 4049", f"no untagged {dst_port}", f"no tagged {dst_port}"]
                )
                self._connection.send_configuration(
                    [f"interface {dst_port}", "no mtu", "no switchport", "no portmode hybrid"]
                )
                self._connection.send_configuration(
                    [
                        f"monitor session {session}",
                        f"source {src_port} destination {dst_port} direction rx",
                    ]
                )
            else:
                raise ValueError("Session ID Requested to be Added is Already Defined!")

        else:
            output = self._connection.send_command('show running-config | grep "monitor session"')

            if any_match(output, session, flags=re.I):
                self._connection.send_configuration(
                    [
                        f"no monitor session {session}",
                        f"interface {dst_port}",
                        f"mtu {self.MAXIMUM_FRAME_SIZE:d}",
                        "portmode hybrid",
                        "switchport",
                    ]
                )
            else:
                raise ValueError("Session ID Requested to be Removed Cannot Be Found.")

    def delete_port_dcb_map(self, port: str, dcbmap: str) -> None:
        """
        Delete a given DCB-MAP from the switch port.

        :param port: switch port in Dell format
        :param dcbmap: str DCB-MAP name
        """
        self._connection.send_configuration([f"interface {port}", f"no dcb-map {dcbmap}"])

    def set_port_flowcontrol(self, port: str, rx: bool, tx: bool) -> None:
        """
        Set flowcontrol on port.

        :param port: switch port in Dell format
        :param rx: rx value to set
        :param tx: tx value to set
        """
        rx = "on" if rx else "off"
        tx = "on" if tx else "off"
        self._connection.send_configuration([f"interface {port}", f"flowcontrol rx {rx} tx {tx}"])

    def disabling_iscsi_app(self, port: str) -> None:
        """
        Turn off the advertisement DCBx-appln-tlv iscsi on port.

        :param port: switch port in Dell format
        """
        self._validate_configure_parameters(ports=port)
        self._connection.send_configuration([f"interface {port}", "protocol lldp", "no advertise DCBx-appln-tlv iscsi"])

    def enable_iscsi_app(self, port: str) -> None:
        """
        Turn on the advertisement DCBx-appln-tlv iscsi on port.

        :param port: switch port in Dell format.
        """
        self._validate_configure_parameters(ports=port)
        self._connection.send_configuration([f"interface {port}", "protocol lldp", "advertise DCBx-appln-tlv iscsi"])

    def disable_pfc_tlv(self, port: str) -> None:
        """
        Disable PFC-TLV on the switch-port.

        :param port: switch port in Dell format.
        """
        self._validate_configure_parameters(ports=port)
        self._connection.send_configuration([f"interface {port}", "protocol lldp", "no advertise dcbx-tlv pfc"])

    def enable_pfc_tlv(self, port: str) -> None:
        """
        Enable PFC-TLV on the switch-port.

        :param port: switch port in Dell format.
        """
        self._validate_configure_parameters(ports=port)
        self._connection.send_configuration([f"interface {port}", "protocol lldp", "advertise dcbx-tlv pfc"])

    def create_qos_conf_on_switch_port(self, port: str) -> None:
        """
        Enable PFC-TLV on the switch-port.

        :param port: switch port in Dell format.
        """
        self._connection.send_configuration(
            [
                f"interface {port}",
                "mtu 9416",
                "portmode hybrid",
                "switchport",
                "protocol lldp",
                "advertise management-tlv management-address system-capabilities system-description system-name",
            ]
        )

    def set_tagged_vlan_on_switch_port(self, vlan: str, port: str) -> None:
        """
        Set tagged vlan on switch port.

        :param port: switch port in Dell format.
        :param vlan: vlan interface in switch in str format.
        """
        self._connection.send_configuration([f"interface vlan {vlan}", f"tagged {port}"])

    def remove_qos_conf_on_switch_port(self, port: str) -> None:
        """
        Destroy DCB configuration on switch port.

        :param port: switch port in Dell format.
        :param vlan: vlan interface in switch in str format.
        """
        self._connection.send_configuration(
            [
                f"interface {port}",
                "no protocol lldp",
            ]
        )
