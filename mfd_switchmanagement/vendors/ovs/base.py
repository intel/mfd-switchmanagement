# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Open vSwitch."""

import logging
import re
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_switchmanagement.exceptions import SwitchConnectionException, SwitchException

if TYPE_CHECKING:
    from mfd_connect import Connection


logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)

REVALIDATOR_CMD = "n-revalidator-threads=1"
HANDLER_CMD = "n-handler-threads=1"


class Ovs:
    """Class for Open Virtual Switch."""

    def __init__(self, connection: "Connection"):
        """
        Initialize Open vSwitch.

        :param connection: Object of mfd-connect representing connection to the host.
        """
        self._conn = connection
        self._check_if_available()

    def vsctl_show(self, bridge: str | None = None) -> str:
        """
        Display an overview of the configuration of Open vSwitch.

        :param bridge: Name of the bridge the details will be displayed for (all bridges if None).
        :return: Details of the selected bridge.
        """
        output = self._conn.execute_command(f"ovs-vsctl show {bridge if bridge else ''}")
        return output.stdout

    def dpctl_show(self, bridge: str) -> str:
        """
        Display an overview of the current configuration of the Open vSwitch datapath for selected bridge.

        :param bridge: Name of the bridge the details will be displayed for.
        :return: Details of the selected bridge.
        """
        output = self._conn.execute_command(f"ovs-dpctl show {bridge}")
        return output.stdout

    def ofctl_show(self, bridge: str | None = None) -> str:
        """
        Display detailed information about the Open vSwitch bridge.

        :param bridge: Name of the bridge the details will be displayed for (all bridges if None).
        :return: Details of the selected bridge.
        """
        output = self._conn.execute_command(f"ovs-ofctl show {bridge if bridge else ''}")
        return output.stdout

    def add_bridge(self, name: str) -> None:
        """
        Add bridge with given name.

        :param name: name of the bridge to be added.
        """
        cmd = f"ovs-vsctl add-br {name}"
        self._conn.execute_command(cmd)

    def del_bridge(self, name: str) -> None:
        """
        Delete bridge with given name.

        :param name: name of bridge to delete.
        """
        cmd = f"ovs-vsctl del-br {name}"
        self._conn.execute_command(cmd)

    def add_port(self, bridge: str, port: str) -> None:
        """Add given port to bridge.

        :param bridge: bridge to add to.
        :param port: port name to add.
        """
        cmd = f"ovs-vsctl add-port {bridge} {port}"
        self._conn.execute_command(cmd)

    def add_port_vxlan_type(self, bridge: str, port: str, local_ip: str, remote_ip: str, dst_port: int) -> None:
        """
        Add vxlan port to the Open vSwitch bridge.

        :param bridge: Name of the bridge to add the vxlan port to.
        :param port: Name of the vxlan port to add.
        :param local_ip: Local IP address for the VXLAN tunnel endpoint.
        :param remote_ip: IP address of the remote VXLAN tunnel.
        :param dst_port: The UDP destination port to use for the VXLAN tunnel.
        """
        cmd = (
            "ovs-vsctl "
            f"add-port {bridge} {port} -- set interface "
            f"{port} type=vxlan options:local_ip={local_ip}"
            f" options:remote_ip={remote_ip}"
            f" options:dst_port={dst_port}"
        )
        self._conn.execute_command(cmd)

    def add_p4_device(self, p4_id: int) -> None:
        """
        Add P4 device.

        :param p4_id: P4 device ID.
        """
        cmd = f"ovs-vsctl add-p4-device {p4_id}"
        self._conn.execute_command(cmd)

    def add_bridge_p4(self, bridge: str, p4_id: int) -> None:
        """
        Add bridge p4 type.

        :param bridge: Name of bridge.
        :param p4_id: P4 device ID.
        """
        cmd = f"ovs-vsctl add-br-p4 {bridge} {p4_id}"
        self._conn.execute_command(cmd)

    def del_port(self, bridge: str, port: str) -> None:
        """
        Delete given port from the bridge.

        :param bridge: Open vSwitch bridge to delete a port from.
        :param port: Port to be deleted.
        """
        cmd = f"ovs-vsctl del-port {bridge} {port}"
        self._conn.execute_command(cmd)

    def get_version(self) -> str:
        """
        Get version of OvS.

        :return: OvS version.
        :raise SwitchException: If ovs-vsctl results in error.
        :raise SwitchConnectionException: When ovs-vsctl -V output does not match the expected critera.
        """
        cmd = "ovs-vsctl -V"
        proc = self._conn.execute_command(cmd)
        if proc.return_code:
            raise SwitchException("Failed to fetch ovs version.")
        else:
            ver = re.search(r"\d+\.\d+\.\d+", proc.stdout)
            if ver:
                return ver.group()
            else:
                raise SwitchConnectionException("Cannot get version of OvS")

    def set_vlan_tag(self, interface: str, vlan: str) -> None:
        """
        Set VLAN tag on the interface.

        :param interface: Interface to set the vlan tag on.
        :param vlan: VLAN id to set.
        """
        cmd = f"ovs-vsctl set port {interface} tag={vlan}"
        self._conn.execute_command(cmd)

    def set_vlan_trunk(self, interface: str, vlans: list[str]) -> None:
        """
        Set multiple VLAN tags on the interface (trunk).

        :param interface: Interface to set the vlan trunks.
        :param vlans: List of VLAN ids to set.
        """
        cmd = f"ovs-vsctl set port {interface} trunks={','.join(vlans)}"
        self._conn.execute_command(cmd)

    def del_flows(self, bridge: str, port_name: str) -> None:
        """
        Delete OpenFlow rules (flows) from an Open vSwitch bridge that match input port.

        :param bridge:  The name of the OVS bridge to delete the flows from.
        :param port_name: Name of the port for which all matching flows will be deleted.
        """
        cmd = f"ovs-ofctl del-flows {bridge} in_port={port_name}"
        self._conn.execute_command(cmd)

    def dpctl_dump_flows(self, bridge: str | None = None) -> str:
        """
        Display the flow installed on the Open vSwitch bridge.

        :param bridge: Name of the bridge.
        :return: View of the current flow table entries in the specified OVS bridge.
        """
        cmd = f"ovs-dpctl dump-flows {bridge if bridge else ''}"
        return self._conn.execute_command(cmd).stdout

    def ofctl_dump_flows(self, bridge: str) -> str:
        """
        Display OpenFlow flows for specific bridge.

        :param bridge: Name of the bridge.
        :return: All flow entries for specified bridge.
        """
        cmd = f"ovs-ofctl dump-flows {bridge}"
        return self._conn.execute_command(cmd).stdout

    def dump_port(self, bridge: str) -> str:
        """
        Display information about the datapath ports on the Open vSwitch bridge.

        :param bridge: Bridge name.
        :return: Details about the status and configuration of the ports associated with the datapath.
        """
        cmd = f"ovs-ofctl dump-ports {bridge}"
        return self._conn.execute_command(cmd).stdout

    def set_other_configs(self, commands: list[str]) -> None:
        """
        Set other_configs params using ovs-vsctl set command.

        :param commands: List of settings to be sequentially passed to other_config parameter of Open vSwitch
        """
        for cmd in commands:
            self._conn.execute_command(f"ovs-vsctl set Open_vSwitch . other_config:{cmd}", shell=True)

    def _check_if_available(self) -> None:
        """
        Check if ovs suite is installed by fetching ovs-vsctl version.

        :raise SwitchException: When ovs-vsctl output not available or incorrect.
        """
        try:
            self.get_version()
        except (SwitchException, SwitchConnectionException):
            raise SwitchException("Failed to initialize OVS. ovs-vsctl not available")
