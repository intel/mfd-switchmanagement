# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from textwrap import dedent
from mfd_connect import SSHConnection
from mfd_switchmanagement import Ovs
from mfd_switchmanagement.exceptions import SwitchConnectionException
from mfd_connect.base import ConnectionCompletedProcess


class TestOvs:
    """Class for Open vSwitch tests."""

    @pytest.fixture
    def ovs(self, mocker) -> Ovs:
        ovs = Ovs.__new__(Ovs)
        ovs.__init__ = mocker.create_autospec(ovs.__init__, return_value=None)
        ovs._conn = mocker.create_autospec(SSHConnection, autospec=True)
        return ovs

    def test_vsctl_show_all(self, ovs):
        ovs.vsctl_show()
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl show ")

    def test_vsctl_show_bridge(self, ovs):
        ovs.vsctl_show("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl show br0")

    def test_dpctl_show(self, ovs):
        ovs.dpctl_show("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-dpctl show br0")

    def test_ofctl_show_all(self, ovs):
        ovs.ofctl_show()
        ovs._conn.execute_command.assert_called_once_with("ovs-ofctl show ")

    def test_ofctl_show(self, ovs):
        ovs.ofctl_show("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-ofctl show br0")

    def test_add_bridge(self, ovs):
        ovs.add_bridge("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl add-br br0")

    def test_del_bridge(self, ovs):
        ovs.del_bridge("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl del-br br0")

    def test_add_port(self, ovs):
        ovs.add_port("br0", "eth0")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl add-port br0 eth0")

    def test_add_port_vxlan_type(self, ovs):
        ovs.add_port_vxlan_type("br0", "eth0", "192.168.1.1", "192.168.1.2", 8000)
        ovs._conn.execute_command.assert_called_once_with(
            "ovs-vsctl add-port br0 eth0 -- set interface "
            "eth0 type=vxlan options:local_ip=192.168.1.1"
            " options:remote_ip=192.168.1.2"
            " options:dst_port=8000"
        )

    def test_add_p4_device(self, ovs):
        ovs.add_p4_device(40)
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl add-p4-device 40")

    def test_add_bridge_p4(self, ovs):
        ovs.add_bridge_p4("br0", 50)
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl add-br-p4 br0 50")

    def test_del_port(self, ovs):
        ovs.del_port("br0", "eth0")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl del-port br0 eth0")

    def test_get_version(self, ovs):
        output = dedent(
            """
        ovs - vsctl(Open vSwitch) 3.2.1
        DB Schema 8.4.0
        """
        )
        ovs._conn.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert ovs.get_version() == "3.2.1"
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl -V")

    def test_get_ver_failed(self, ovs):
        ovs._conn.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(SwitchConnectionException, match="Cannot get version of OvS"):
            ovs.get_version()

    def test_set_vlan_tag(self, ovs):
        ovs.set_vlan_tag("eth0", "1")
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl set port eth0 tag=1")

    def test_set_vlan_trunk(self, ovs):
        ovs.set_vlan_trunk("eth0", ["1", "2"])
        ovs._conn.execute_command.assert_called_once_with("ovs-vsctl set port eth0 trunks=1,2")

    def test_del_flows(self, ovs):
        ovs.del_flows("br0", "eth0")
        ovs._conn.execute_command.assert_called_once_with("ovs-ofctl del-flows br0 in_port=eth0")

    def test_dpctl_dump_flows_all(self, ovs):
        ovs.dpctl_dump_flows()
        ovs._conn.execute_command.assert_called_once_with("ovs-dpctl dump-flows ")

    def test_dpctl_dump_flows_bridge(self, ovs):
        ovs.dpctl_dump_flows("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-dpctl dump-flows br0")

    def test_ofctl_dump_flows(self, ovs):
        ovs.ofctl_dump_flows("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-ofctl dump-flows br0")

    def test_dump_port(self, ovs):
        ovs.dump_port("br0")
        ovs._conn.execute_command.assert_called_once_with("ovs-ofctl dump-ports br0")

    def test_set_other_configs(self, ovs, mocker):
        ovs.set_other_configs(["n-revalidator-threads=1", "n-handler-threads=1"])
        ovs._conn.execute_command.assert_has_calls(
            [
                mocker.call("ovs-vsctl set Open_vSwitch . other_config:n-revalidator-threads=1", shell=True),
                mocker.call("ovs-vsctl set Open_vSwitch . other_config:n-handler-threads=1", shell=True),
            ]
        )
