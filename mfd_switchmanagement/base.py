"""Module for base switch class."""

# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
import socket
import typing
from abc import ABC
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from .connections.base import BaseSwitchConnection
from .connections.ssh import SSHSwitchConnection
from .exceptions import SwitchException

if typing.TYPE_CHECKING:
    from pydantic import BaseModel


class FecMode(Enum):
    """Available FEC modes."""

    RS_FEC = "rs-fec"
    FC_FEC = "fc-fec"
    NO_FEC = "no-fec"


@dataclass
class LLDPlink:
    """A local/remote LLDP link pair."""

    loc_portid: str
    rem_portid: str
    rem_devid: str
    rem_sysname: str


def _grouper(iterable: str, group_size: int) -> str:
    """
    Return a string split into groups of 2 characters.

    This is used for converting hex strings into colon format
    'aabbccdd' -> ('aa', 'bb', 'cc', 'dd')

    """
    return (iterable[i : i + group_size] for i in range(0, len(iterable), group_size))


class Switch(ABC):
    """
    Module of switch management.

    Usage:
    >>>switch_details = {
    >>>         'ip'             : '10.10.10.10',
    >>>         'username'       : 'root',
    >>>         'password'       : "***",
    >>>         'secret'         : "***",
    >>>         'connection_type': SSHSwitchConnection,
    >>>         'switch_type'    : Cisco
    >>>     }
    >>>switch_type = switch_details.pop('switch_type')
    >>>switch = switch_type(**switch_details)
    >>>print(switch.show_ports_status())
    Port    Name               Status       Vlan       Duplex  Speed Type
    Te2/1   "TRUNK "       connected    trunk         full    10G 10Gbase-LR
    Te2/2   "TRUNK VM"   connected    trunk         full    10G 10Gbase-LR
    Te2/3   10G Windows 2008 i notconnect   119           full    10G 10Gbase-LR
    Te2/4   "Blank for future  notconnect   107           full    10G 10Gbase-LR
    (...)
    >>>switch.disconnect()
    """

    MINIMUM_FRAME_SIZE = None
    MAXIMUM_FRAME_SIZE = None
    QUAD_REGEX = re.compile(r"([a-f0-9]{4})([a-f0-9]{4})([a-f0-9]{4})")
    MAC_ADDRESS_REGEX = re.compile(r"([a-fA-F0-9]{2}[-:.]?){5}[a-fA-F0-9]{2}")
    WWN_ADDRESS_REGEX = re.compile(r"([a-fA-F0-9]{2}[-:.]?){7}[a-fA-F0-9]{2}")
    PORT_REGEX = None
    PORT_CHANNEL_REGEX = None

    def __init__(
        self,
        ip: str = None,
        username: str = None,
        password: Optional[str] = None,
        secret: Optional[str] = None,
        connection_type: "BaseSwitchConnection" = SSHSwitchConnection,
        use_ssh_key: bool = False,
        ssh_key_file: Union[str, Path] = "",
        auth_timeout: Union[int, float] = 30,
        device_type: Optional[str] = None,
        topology: Optional["BaseModel"] = None,  # SwitchModel
        global_delay_factor: Optional[int] = None,
        *args,
        **kwargs,
    ):
        """Initialize base switch."""
        self._connection = connection_type(
            ip=ip,
            username=username,
            password=password,
            secret=secret,
            use_ssh_key=use_ssh_key,
            ssh_key_file=ssh_key_file,
            auth_timeout=auth_timeout,
            device_type=device_type,
            global_delay_factor=global_delay_factor,
        )

        self.topology = topology

    def _validate_configure_parameters(
        self,
        ports: str,
        mode: Optional[str] = None,
        vlan: Optional[int] = None,
        vlan_type: Optional[str] = None,
    ) -> None:
        """
        Validate parameters.

        :param ports: ports to configure
        :param vlan: VLAN to configure
        :param vlan_type: Tagging mode
        :param mode: Trunking mode
        :raises: ValueError if parameters are incorrect
        """
        self._validate_ports_syntax(ports)

        if vlan_type:
            vlan_type = vlan_type.lower().strip()
            if vlan_type not in ["untagged", "tagged"]:
                raise ValueError(f"Invalid vlan_type flag: {vlan_type}. Valid values are 'tagged' or 'untagged'.")

        if mode:
            mode = mode.lower().strip()

            if mode not in ["access", "trunk"]:
                raise ValueError(f"Invalid mode type: {mode}. Valid values are 'access' or 'trunk'.")
            if not vlan:
                if vlan_type == "untagged":
                    raise ValueError("Vlan Id must be specified when adding untagged vlan.")
                if mode == "access":
                    raise ValueError("Vlan Id must be specified when adding access vlan.")

    def _validate_ports_syntax(self, ports: str) -> None:
        """
        Check if given ports have got correct format.

        :param ports: ports to configure
        :raises ValueError: if format is incorrect
        :raises ValueError: if ports value is empty
        """
        if not ports:
            raise ValueError("Ports value is empty")
        match_port = self.PORT_REGEX.search(ports)
        if not match_port:
            raise ValueError(f"Invalid ports format: {ports}")

    def _validate_port_and_port_channel_syntax(
        self, *, ethernet_port: str = None, port_channel: str = None, both_syntax: str = None
    ) -> None:
        """
        Validate port type syntax to meet ethernet port or port-channel syntax.

        :param ethernet_port: ethernet port if it's syntax is only allowed
        :param port_channel: port-channel if it's syntax is only allowed
        :param both_syntax: ethernet port or port-channel passed here if both syntax are allowed
        :raises ValueError: if port type does not meet syntax requirements.
        """
        match_port = None
        match_port_channel = None

        if ethernet_port:
            match_port = self.PORT_REGEX.search(ethernet_port)

        if port_channel:
            match_port_channel = self.PORT_CHANNEL_REGEX.search(port_channel)

        if both_syntax:
            match_port = self.PORT_REGEX.search(both_syntax)
            match_port_channel = self.PORT_CHANNEL_REGEX.search(both_syntax)

        if ethernet_port and not match_port:
            raise ValueError(f"Port is not in ethernet port syntax! {ethernet_port}")

        if port_channel and not match_port_channel:
            raise ValueError(f"Port is not in port-channel syntax! {port_channel}")

        if both_syntax and not match_port and not match_port_channel:
            raise ValueError(f"Port is not either in ethernet port or port-channel syntax! {both_syntax}")

    def show_version(self) -> str:
        """
        Show switch detailed info for further identification.

        :return: String with version information
        """
        return self._connection.send_command("show version")

    def disconnect(self) -> None:
        """Close connection with switch."""
        self._connection.disconnect()

    def _prepare_port_configuration(self, port: str) -> None:
        res = self.PORT_REGEX.search(port)
        if not port or not res:
            raise ValueError(f"Invalid port list: {port}")

        self._connection.send_command_list(["configure terminal", f"interface range {port}", "switchport"])

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
        raise NotImplementedError("Enabling spanning tree is not implemented for this switch yet")

    def is_mac_address(self, address: str) -> bool:
        """
        Check correctness of mac address.

        :param address: string to check
        :return: correctness as bool
        """
        return True if self.MAC_ADDRESS_REGEX.match(address) else False

    def is_wwn_address(self, address: str) -> bool:
        """
        Check correctness of wwn address.

        :param address: string to check
        :return: correctness as bool
        """
        return True if self.WWN_ADDRESS_REGEX.match(address) else False

    def disable_spanning_tree(self, port: str) -> str:
        """
        Disable spanning tree on given port.

        :param port: port of switch
        :return: Output from disabling
        """
        raise NotImplementedError("Disabling spanning tree is not implemented for this switch yet")

    def shutdown(self, shutdown: bool, port: str) -> None:
        """
        Turn switch port on/off.

        :param shutdown: bool flag for shutdown
        :param port: port of switch
        """
        res = self.PORT_REGEX.search(port)
        if not port or not res:
            raise ValueError(f"Invalid port list: {port}")

        if shutdown:
            self.disable_port(port, 1)
        else:
            self.enable_port(port, 1)

    def enable_port(self, port: str, count: int = 1) -> None:
        """
        Enable port on switch.

        :param port: port of switch
        :param count: number of sending command
        """
        self._prepare_port_configuration(port)
        for _ in range(count):
            self._connection.send_command("no sh")

    def disable_port(self, port: str, count: int = 1) -> None:
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
        raise NotImplementedError("Changing vlan is not implemented for this switch yet")

    def exit_user(self) -> None:
        """Exit to user mode."""
        raise NotImplementedError("Exiting from user mode is not implemented for this switch yet")

    def set_trunking_interface(self, port: str, vlan: int) -> str:
        """
        Change mode to trunk on port and allows vlan traffic on this port.

        :param port: port of switch
        :param vlan: vlan to set
        :return: Output from setting
        """
        raise NotImplementedError("Setting trunk interface is not implemented for this switch yet")

    def show_port_running_config(self, port: str) -> str:
        """
        Show running config on given port.

        :param port: port of switch
        """
        raise NotImplementedError("Showing running config on port is not implemented for this switch yet")

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        raise NotImplementedError("Checking link status on port is not implemented for this switch yet")

    def set_fec(self, port: str, fec_mode: "FecMode") -> None:
        """
        Set Forward error correction on port.

        :param port: port of switch
        :param fec_mode: Value of FEC
        :raises SwitchException on failure
        """
        raise NotImplementedError("Error: this operation is feasible for 25G switches only")

    def get_fec(self, port: str) -> str:
        """
        Get Forward error correction on port.

        :param port: port of switch
        :return: FEC Mode
        """
        raise NotImplementedError("Error: this operation is feasible for 25G switches only")

    def disable_jumbo_frame(self, port: str) -> None:
        """
        Disable MTU on port(s) (restore to default value).

        :param port: port of switch
        """
        raise NotImplementedError("Disable jumbo frame is not implemented for this switch yet")

    def default_ports(self, ports: str) -> None:
        """
        Set ports to default configuration.

        :param ports: ports to configure
        :raises ValueError if parameter is invalid
        """
        raise NotImplementedError("Set port to default configuration is not implemented for this switch yet")

    def enable_jumbo_frame(self, frame_size: int, port: str) -> None:
        """
        Set MTU on port(s).

        :param port: port of switch
        :param frame_size: value to set
        """
        raise NotImplementedError("Enable jumbo frame is not implemented for this switch yet.")

    def enable_max_jumbo(self, port: str) -> None:
        """
        Set max available MTU on port(s).

        :param port: port of switch
        """
        self.enable_jumbo_frame(self.MAXIMUM_FRAME_SIZE, port)

    def get_port_by_mac(self, mac: str) -> str:
        """
        Get port with the specified MAC address.

        :param mac: mac address to find port
        :return: port name
        :raises SwitchException: if port not found
        :raises ValueError: if provided MAC address is incorrect
        """
        raise NotImplementedError("Get port by MAC is not implemented for this switch yet")

    def get_lldp_port(self, mac: str) -> str:
        """
        Get the lldp port with the specified MAC address.

        :param mac: mac address to find port
        :return: port name or None if not found
        """
        raise NotImplementedError("Get LLDP port is not implemented for this switch yet")

    def get_lldp_neighbors(self) -> List[LLDPlink]:
        """
        Get the lldp neighbors for switch.

        :return: list of LLDPlinks
        """
        raise NotImplementedError("Get LLDP neighbors is not implemented for this switch yet")

    def get_port_dcbx_version(self, port: str) -> str:
        """
        Get dcbx version of switch port.

        :param port: port of switch
        :return: port name or None if not found
        """
        raise NotImplementedError("Get port DCBX version is not implemented for this switch yet")

    def set_dcb_qos_conf(self, port: str, dcb_map: str, dcb_tc_info_list: List) -> None:
        """
        Configure DCB traffic on the switch port.

        :param port: port of switch
        :param dcb_map: switch DCB map name to assign
        :param dcb_tc_info_list: DCB traffic class info list.
        length of list has to be 3 or less (str traffic_class, str bandwidth, str pfc='off')
        """
        raise NotImplementedError("Set dcb QoS conf is not implemented for this switch yet")

    def get_dcb_bw_by_up(self, port: str, dcb_map: str, up: int) -> str:
        """
        Get bandwidth of DCB traffic class from the switch port.

        :param port: switch port to configure
        :param dcb_map: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: traffic class bandwidth percent
        """
        raise NotImplementedError("Get dcb bw by user priority is not implemented for this switch yet")

    def get_dcb_tc_by_up(self, port: str, dcb_map: str, up: int) -> str:
        """
        Retrieve traffic class by user priority for given port or dcb_map.

        :param port: switch port to configure
        :param dcb_map: switch DCB map name to assign
        :param up: user priority (0 ~ 7)
        :return: assigned traffic class for user priority
        """
        raise NotImplementedError("Get dcb tc by user priority is not implemented for this switch yet")

    def set_port_dcbx_version(self, port: str, mode: str) -> None:
        """
        Set the DCBX version for the switch port.

        :param port: switch port
        :param mode: DCBX mode
        """
        raise NotImplementedError("Set port dcbx version is not implemented for this switch yet")

    def get_port_dcb_map(self, port: str) -> str:
        """
        Get the DCB MAP name applied to a given switch port.

        :param port: switch port
        :return: DCB MAP name
        """
        raise NotImplementedError("Get port dcb map is not implemented for this switch yet")

    def set_port_dcb_map(self, port: str, dcbmap: str) -> None:
        """
        Set the DCB MAP for a switch port to a given name.

        :param port: port of switch
        :param dcbmap: DCB-MAP name
        """
        raise NotImplementedError("Set port dcb map is not implemented for this switch yet")

    def set_dcb_map_tc(self, dcbmap: str, tc: int, bw: int, pfc: str) -> None:
        """
        Configure a DCB MAP with TC, BW and PFC settings.

        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :param bw: Bandwidth %
        :param pfc: PFC state
        """
        raise NotImplementedError("Set dcp map tc is not implemented for this switch yet")

    def set_dcb_map_up(self, dcbmap: str, up: str) -> None:
        """
        Set a User Priority Group on a DCB MAP.

        :param dcbmap: DCB-MAP name
        :param up: User Priority Group
        """
        raise NotImplementedError("Set dcb map user priority is not implemented for this switch yet")

    def delete_dcb_map(self, port: str, dcbmap: str) -> None:
        """
        Delete a given DCB-MAP from the switch port and switch config.

        :param port: port of switch
        :param dcbmap: DCB-MAP name
        """
        raise NotImplementedError("Delete dcb map is not implemented for this switch yet")

    def get_dcb_map_bw_by_tc(self, dcbmap: str, tc: int) -> str:
        """
        Get the bandwidth percentage of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: Traffic Class
        :return: Bandwidth value
        """
        raise NotImplementedError("Get dcb map bw by tc is not implemented for this switch yet")

    def get_dcb_map_pfc_by_tc(self, dcbmap: str, tc: int) -> str:
        """
        Get the PFC state of traffic class in DCB MAP.

        :param dcbmap: DCB-MAP name
        :param tc: int Traffic Class
        :return: PFC state
        """
        raise NotImplementedError("Get dcb map pfc by tc is not implemented for this switch yet")

    def get_dcb_map_pfc(self, dcbmap: str) -> str:
        """
        Get the global PFC state for a given DCB MAP.

        :param dcbmap: DCB-MAP name
        :return: PFC state
        """
        raise NotImplementedError("Get dcb map pfc is not implemented for this switch yet")

    def get_tc_by_up(self, up: int) -> int:
        """
        Retrieve traffic class by user priority for given port.

        :param up: QoS priority (0 ~ 7)
        :return: assigned traffic class for user priority
        """
        raise NotImplementedError("Get tc by up is not implemented for this switch yet")

    def change_standard_to_switch_mac_address(self, address: str) -> str:
        """
        Convert standard mac address to switch mac address format.

        :param address: any mac address (no separators, separated using -:., lowecase, uppercase etc.
        :return: MAC address in switch accepted format (AA:BB:CC:DD:EE:FF)
        """
        # remove delimiters
        hex_bytes = address.lower()

        for c in ":.-":
            hex_bytes = hex_bytes.replace(c, "")

        # abba.abba.abba
        quad_dots = ".".join(self.QUAD_REGEX.match(hex_bytes).groups())
        return quad_dots

    def change_switch_to_linux_mac_address(self, address: str) -> str:
        """
        Convert switch mac address to linux mac address format.

        :param address: any mac address
        :return: mac address in linux format
        """
        if re.match(r"([a-f0-9]{4})\.([a-f0-9]{4})\.([a-f0-9]{4})", address):
            hex_bytes = address.lower()
            for c in ":.-":
                hex_bytes = hex_bytes.replace(c, "")
            # ab:ba:ab:ba:ab:ba
            return ":".join(_grouper(hex_bytes, 2))
        else:
            raise TypeError("Invalid quad dot mac address {0}".format(address))

    def change_standard_to_switch_IPv4_address(self, address: str) -> str:
        """
        Convert standard IP address to switch IP address format.

        :param address: any mac address
        :return: mac address in linux format
        """
        # Chassis ID: 10.03.00.243
        octets = (int(o) for o in address.split("."))
        return ".".join("{0:02d}".format(o) for o in octets)

    def change_standard_to_switch_IPv6_address(self, address: str) -> str:
        """
        Convert standard IP address to switch IP address format.

        :param address: any mac address
        :return: mac address in IPv6 switch format
        """
        raise NotImplementedError("Change standard to switch IPv6 address is not implemented for this switch yet")

    def change_switch_to_standard_IPv4_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv4 standard format
        """
        # Chassis ID: 10.03.00.243
        return socket.inet_ntoa(socket.inet_aton(address))

    def change_switch_to_standard_ipv6_address(self, address: str) -> str:
        """
        Convert switch IP address to standard IP address format.

        :param address: any mac address
        :return: mac address in IPv6 standard format
        """
        raise NotImplementedError("Change switch to standard IPv6 address is not implemented for this switch yet")

    def get_vlan_by_mac(self, mac: str) -> int:
        """
        Get VLAN of port with the specified MAC address.

        :param mac: device MAC address in AA:BB:CC:DD:EE:FF form
        :return: VLAN ID
        :raises SwitchException: if VLAN not found
        :raises ValueError: if provided MAC address is incorrect
        """
        raise NotImplementedError("Get VLAN by MAC is not implemented for this switch yet")

    def canonicalize_chassis_id_tlv(self, tlv: str) -> str:
        """
        Convert tlv to correct format.

        :param tlv: TLV address
        :return: correct address
        :raises SwitchException: if could not convert to correct format
        """
        try:
            return self.change_switch_to_linux_mac_address(tlv)
        except TypeError:
            pass
        try:
            return self.change_switch_to_standard_ipv6_address(tlv)
        except (socket.error, TypeError):
            pass
        try:
            return self.change_switch_to_standard_IPv4_address(tlv)
        except socket.error:
            pass
        raise SwitchException(f"Could not convert tlv {tlv} to correct format")

    def canonicalize_port_id_tlv(self, tlv: str) -> str:
        """
        Convert tlv to correct format.

        :param tlv: TLV address
        :return: correct address
        """
        return self.canonicalize_chassis_id_tlv(tlv)

    def get_port_speed(self, port: str) -> int:
        """
        Get the speed of the desired port, speed is represented in Mbit.

        :param port: Port on the switch from which speed should be gathered.
        :return: Detected port speed in Mbit format.
        :raise: SwitchException when speed can't be gathered from switch.
        """
        raise NotImplementedError("Get port speed is not implemented for this switch.")

    def get_max_mtu_frame_size(self) -> int:
        """
        Get the maximum MTU frame size for Switch.

        return: maximum MTU frame size.
        raise: SwitchException if maximum mtu frame size is not found.
        """
        raise NotImplementedError("Get max mtu frame size is not implemented for this switch.")
