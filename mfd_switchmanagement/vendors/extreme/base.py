# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Extreme base."""

import re
from typing import Optional, List

from ...base import Switch
from ...exceptions import SwitchException
from ...utils.match import any_match


class Extreme(Switch):
    """Implementation of Extreme Switch."""

    MINIMUM_FRAME_SIZE = 1523
    MAXIMUM_FRAME_SIZE = 9216
    PORT_REGEX = re.compile(r"^(\d+)([,-]\d+)*$")
    MAXIMUM_SUPPORT_TRAFFIC_CLASSES = 8
    VALID_SPEED = [1000, 2500, 5000, 10000]
    QOS_PRIORITY = [0, 1, 2, 3, 4, 5, 6, 7]

    def get_max_mtu_frame_size(
        self,
    ) -> int:
        """Return maximum MTU frame size for Extreme Switch."""
        return self.MAXIMUM_FRAME_SIZE

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command("show version detail")

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        self._validate_configure_parameters(ports=port)

        if shutdown:
            arg = "disable"
        else:
            arg = "enable"
        arg += " port " + port
        self._connection.send_command(arg)

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

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Enable jumbo frame.

        :param frame_size: Size of frame
        :param port: port of switch
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command(f"configure jumbo-frame-size {frame_size}")
        self._connection.send_command(f"enable jumbo-frame port {port}")

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable jumbo frame.

        :param port: Port to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=port)

        self._connection.send_command(f"disable jumbo-frame port {port}")

    def default_ports(self, ports: str) -> None:
        """
        Set port to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        self._validate_configure_parameters(ports=ports)

        self._connection.send_command(f"configure jumbo-frame-size {self.MAXIMUM_FRAME_SIZE}")
        self._connection.send_command(f"enable jumbo-frame port {ports}")

        self._connection.send_command("disable clipaging")
        output = self._connection.send_command(f"show vlan port {ports}")
        response = re.findall(r"^(\S+)\s+\d+\s", output, re.M)
        for res in response:
            self._connection.send_command(f"configure vlan {res} delete port {ports}")

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
            raise ValueError(f"Invalid MAC address: {mac}")

        self._connection.send_command("disable clipaging")
        output = self._connection.send_command(f"show fdb {mac}")
        for line in output.splitlines():
            if mac in line.lower():
                return line.split()[-1]

        output = self._connection.send_command("show lldp neighbors")
        for line in output.splitlines():
            if mac in line.lower():
                return line.split()[0]

        raise SwitchException(f"Could not find port for MAC address {mac}")

    def delete_mat_entry(self, mac: str) -> None:
        """
        Delete MAC address-table entry.

        :param mac: MAC to delete
        :raises ValueError: if provided MAC address is incorrect
        """
        if not self.is_mac_address(mac):
            raise ValueError(f"Invalid MAC address: {mac}")

        self._connection.send_command(f"clear fdb {mac}")

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
            raise ValueError(f"Invalid MAC address: {mac}")

        self._connection.send_command("disable clipaging")
        output = self._connection.send_command(f"show fdb {mac}")
        lines = output.splitlines()
        for line in lines:
            if mac in line.lower():
                fields = line.split()
                val = fields[1].split("(")[1].split(")")[0]
                return int(val)

        output = self._connection.send_command("show lldp neighbors")
        for line in output.splitlines():
            if mac in line.lower():
                port = line.split()[0]
                output = self._connection.send_command(f"show port {port} information detail")
                next_line = False
                for port_details_line in output.splitlines():
                    if next_line:
                        return int(port_details_line.split("Tag = ")[1].split(",")[0])
                    if "VLAN cfg:" in port_details_line:
                        next_line = True

        raise SwitchException(f"Could not find VLAN for MAC address {mac}")

    def configure_vlan(self, ports: str, vlan: int, vlan_type: str, mode: str) -> None:
        """
        Configure vlan.

        Set trunking and tagging mode, create vlan if required, enable port

        :param ports: port to configure
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=ports, vlan_type=vlan_type)
        self._connection.send_command("disable clipaging")
        output = self._connection.send_command("show vlan")
        vlan_regex = rf"^(\S+)\s+{vlan}\s"
        res = re.search(vlan_regex, output, re.M)
        if not res:
            self._connection.send_command(f"create vlan {vlan}")
            output = self._connection.send_command("show vlan")
            res = re.search(vlan_regex, output, re.M)
            if not res:
                raise SwitchException(f"VLAN with ID: {vlan} not configured on switch")
        vlan = res.group(1)
        self._connection.send_command(f"configure vlan {vlan} add port {ports} {vlan_type}")

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

        self._connection.send_configuration([f"delete vlan {vlan}"])

        # verify VLAN is completely removed
        output = self._connection.send_command("show vlan")
        vlan_regex = rf"^(\S+)\s+{vlan}\s"
        res = re.search(vlan_regex, output, re.M)
        return bool(not res)

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set dcbx version of port.

        :param port: port to configure
        :param mode: version
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        dcbx = any_match(mode, r"(\bCEE|\bIEEE)", flags=re.I)
        if not dcbx:
            raise ValueError("Invalid DCBX value, must be either 'CEE' or 'IEEE'")

        if mode == "cee":
            mode = "baseline"

        self._connection.send_command(
            f'configure lldp port {port} no-advertise vendor-specific dcbx {"baseline" if mode == "ieee" else "ieee"}'
        )
        self._connection.send_command(f"configure lldp port {port} advertise vendor-specific dcbx {mode}")

    def clear_port_dcbx(self, port: str) -> None:
        """
        Delete dcbx of port.

        :param port: port to configure
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        for dcbx_param in ["baseline", "ieee"]:
            self._connection.send_command(f"configure lldp port {port} no-advertise vendor-specific dcbx {dcbx_param}")

    def show_port_dcbx(self, port: str) -> str:
        """
        Show dcbx configuration including peer info.

        :param port: port
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        output = self._connection.send_command(f"show lldp ports {port} dcbx detail")
        return output

    def set_port_speed(self, port: str, speed: int) -> None:
        """
        Set the speed for the switch port.

        :param port: switch port in Extreme format
        :param speed: speed value
        :raises ValueError if parameters are invalid
        """
        self._validate_configure_parameters(ports=port)

        if speed not in self.VALID_SPEED:
            raise ValueError(f"Invalid speed value: [{speed:d}], must be one of: {self.VALID_SPEED}")

        self._connection.send_command(f"configure port {port} auto on speed {speed:d} duplex full")

    def get_dcb_map_bw_by_tc(self, dcbmap: Optional[str], tc: int, port: str = None) -> str:
        """
        Get the bandwidth percentage of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :param port: switch port in Extreme format
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if not port:
            raise ValueError("Need specify port number to get bandwidth by traffic class")

        if tc >= self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(f"Extreme switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:d} traffic classes.")

        output = self._connection.send_command(f"show qosprofile port {port} | grep QP{tc:d}")
        bandwidth = any_match(output, rf"((QP{tc:d})\s*(MinBw\s*=\s*(\d+)))", flags=re.I)
        try:
            return bandwidth[0][3]
        except IndexError:
            raise SwitchException(f"Error retrieving bandwidth percentage for port {port}, PG {tc}")

    def get_tc_by_up(self, up: int) -> int:
        """
        Get the traffic class from user priority.

        :param up: QoS priority (0 ~ 7)
        :raises ValueError if parameters are invalid
        :raises SwitchException on failure
        """
        if up not in self.QOS_PRIORITY:
            raise ValueError(f"QoS priority has to be between {self.QOS_PRIORITY[0]} and {self.QOS_PRIORITY[-1]}.")

        output = self._connection.send_command("show dot1p")
        tc = any_match(output, rf"(\s+({up})\s+QP(\d))", flags=re.I)
        if tc:
            return int(tc[0][2])  # todo remove not used groups from regex
        else:
            raise SwitchException("Error retrieving traffic class by user priority.")

    def get_dcb_bw_by_up(self, port: str, dcbmap: str, up: int) -> str:
        """
        Get bandwidth of DCB traffic class from the switch port.

        :param port: switch port to configure
        :param dcbmap: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: traffic class bandwidth percent
        """
        return str(self.get_dcb_map_bw_by_tc(None, self.get_tc_by_up(up), port))

    def set_port_pfc_by_tc(self, port: str, qos_priority: int, pfc: str) -> None:
        """
        Configure PFC settings.

        :param port: switch port in Extreme format
        :param qos_priority: QoS priority (0 ~ 7)
        :param pfc: str PFC state
        :raises ValueError if parameters are invalid
        """
        pfc_mode = any_match(pfc, r"(\bon|\boff)", flags=re.I)
        if not pfc_mode:
            raise ValueError("Invalid pfc value, must be either 'on' or 'off'")

        mode = "enable" if pfc == "on" else "disable"
        self._connection.send_command(f"disable flow-control tx-pause ports {port}")
        self._connection.send_command(f"{mode} flow-control tx-pause priority {qos_priority} port {port}")
        self._connection.send_command(
            f"{mode} flow-control rx-pause qosprofile QP{self.get_tc_by_up(qos_priority)} " f"port {port}"
        )

    def delete_port_pfc(self, port: str) -> None:
        """
        Delete the PFC settings.

        :param port: switch port in Extreme format
        """
        self._validate_configure_parameters(ports=port)

        for i in self.QOS_PRIORITY:
            self._connection.send_command(f"disable flow-control rx-pause qosprofile QP{i + 1} port {port}")
            self._connection.send_command(f"disable flow-control tx-pause priority {i} port {port}")

    def set_port_bw_by_tc(self, port: str, bandwidth: List[int], suffix: Optional[str] = None) -> None:
        """
        Set the bandwidth of traffic class on a selected port.

        :param port: switch port in Extreme format
        :param bandwidth: list of bandwidth
        :param suffix: suffix for names, there will be no effect for Extreme switches
        :raises ValueError if parameters are invalid
        """
        if len(bandwidth) > self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES:
            raise ValueError(f"Extreme switch supports up to {self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES} traffic classes.")

        if not all(isinstance(n, int) for n in bandwidth):
            raise ValueError("Bandwidth list has invalid elements. Must be list of int.")

        if sum(bandwidth) > 100:
            raise ValueError("Bandwidth exceeded. Value on port cannot exceed 100%.")

        self.delete_port_bw_by_tc(port)

        for i, item in enumerate(bandwidth):
            self._connection.send_command(f"configure qosprofile QP{i + 1} minbw {item} maxbw 100 ports {port}")

    def delete_port_bw_by_tc(self, port: str, suffix: Optional[str] = None) -> None:
        """
        Delete the bandwidth of traffic class on a selected port.

        :param port: switch port in Extreme format
        :param suffix: suffix for names (not used on Extreme)
        """
        for i in range(self.MAXIMUM_SUPPORT_TRAFFIC_CLASSES):
            self._connection.send_command(f"configure qosprofile QP{i + 1} minbw 0 maxbw 100 ports {port}")

    def get_port_speed(self, port: str) -> int:
        """
        Get the speed of the desired port, speed is represented in Mbit.

        :param port: Port including speed prefix (e.g. Eth1/1) on the switch from which speed should be gathered
        :return: Detected port speed in Mbit format.
        :raise: SwitchException when speed can't be gathered from switch.
        """
        gigabit_multiplier = 1000
        output = self._connection.send_command(f"show ports {port} no-refresh")
        speed = re.search(r"(?P<speed>\d+)G\s", output, re.M)
        if speed:
            return int(speed.group("speed")) * gigabit_multiplier
        else:
            raise SwitchException(f"Couldn't retrieve port speed for port: {port} in output: {output}")
