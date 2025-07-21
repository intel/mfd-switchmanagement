# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from pytest import fixture, raises
from textwrap import dedent

from mfd_switchmanagement import Arista
from mfd_switchmanagement.connections.ssh import SSHSwitchConnection
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.vendors.arista.base import FecMode


class TestArista:
    """Class for Arista tests."""

    @fixture
    def switch(self, mocker) -> Arista:
        switch = Arista.__new__(Arista)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        switch._connection = mocker.create_autospec(SSHSwitchConnection)
        return switch

    def test_get_port_by_mac(self, switch, mocker):
        out = dedent(
            """\
        Arista-1A>show mac address-table
        Mac Address Table
        ------------------------------------------------------------------

        Vlan Mac Address Type Ports Moves Last Move
        ---- ----------- ---- ----- ----- ---------
        1 0000.0000.0314 DYNAMIC Et11/3/0 1 27 days, 20:34:21 ago
        1 0000.0000.0315 DYNAMIC Et11/3/1 1 27 days, 20:34:21 ago
        1 0000.0000.0316 DYNAMIC Et11/3/2 1 27 days, 20:34:21 ago"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_by_mac("00:00:00:00:03:14") == "Et11/3/0"

    def test_get_port_by_mac_alternate_id(self, switch, mocker):
        out = dedent(
            """\
        Arista-1A>show mac address-table
        Mac Address Table
        ------------------------------------------------------------------

        Vlan Mac Address Type Ports Moves Last Move
        ---- ----------- ---- ----- ----- ---------
        1 0000.0000.0314 DYNAMIC Et123 1 27 days, 20:34:21 ago
        1 0000.0000.0315 DYNAMIC Et40 1 27 days, 20:34:21 ago
        1 0000.0000.0316 DYNAMIC Et41 1 27 days, 20:34:21 ago"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_by_mac("00:00:00:00:03:14") == "Et123"

    def test_get_port_speed(self, switch, mocker):
        out = """
              Port       Name   Status       Vlan     Duplex Speed  Type         Flags Encapsulation
              Et19/1            notconnect   600      full   25G    40GBASE-CR4jf3418-18A2-tsw-30041#
              """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_speed("Et19/1") == 25000

    def test_get_port_speed_corrupted_output(self, switch, mocker):
        out = """
              Port       Name   Status       Vlan     Duplex Speed  Type         Flags Encapsulation
              Et19/1          ###################################sw-30041#
              """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Couldn't retrieve port speed for port"):
            switch.get_port_speed("Et19/1")

    @pytest.mark.parametrize("expected", ["speed forced 100gfull", "speed auto 25gfull", ""])
    def test__get_speed_command_from_configuration(self, switch, mocker, expected):
        out = dedent(
            f"""\
        interface Ethernet9/1
           {expected}
           no error-correction encoding"""
        )  # noqa W391
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch._get_speed_command_from_configuration("Eth9/1") == expected

    @pytest.mark.parametrize("expected_command", ["speed forced 100", ""])
    def test_default_ports(self, switch, mocker, expected_command):
        expected_list = [
            "configure terminal",
            "default interface Eth9/1",
            "interface Eth9/1",
            "default switchport",
            "default mtu",
            expected_command,
        ]
        switch._validate_configure_parameters = mocker.Mock()
        switch._get_speed_command_from_configuration = mocker.Mock(return_value=expected_command)
        switch.default_ports("Eth9/1")
        switch._connection.send_command_list.assert_called_once_with(expected_list)

    def test_disable_fec_true(self, switch, mocker):
        expected_output = dedent(
            """
        Interface           Configured              Available                                              Operational
        ----------------    --------------------    ----------------------------------------------------   -----------
        Ethernet3/1         Default                 Reed-Solomon                                           Disabled
        """
        )
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock(side_effect=["", expected_output])
        assert switch.disable_fec("Ethernet3/1") is True

    def test_disable_fec_false(self, switch, mocker):
        expected_output = dedent(
            """
        Interface           Configured              Available                                              Operational
        ----------------    --------------------    ----------------------------------------------------   -----------
        Ethernet3/1         Default                 Reed-Solomon                                           Reed-Solomon
        """
        )
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock(side_effect=["", expected_output])
        assert switch.disable_fec("Ethernet3/1") is False

    def test_disable_fec_raises_exception(self, switch, mocker):
        expected_output = ""
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock(side_effect=["", expected_output])
        with pytest.raises(SwitchException, match="Cannot recognize Forward Error Correction status"):
            switch.disable_fec("Ethernet3/1")

    def test_get_fec_fc(self, switch, mocker):
        expected_output = dedent(
            """
        Interface           Configured              Available                                              Operational
        ----------------    --------------------    ----------------------------------------------------   -----------
        Ethernet3/1         Default                 Fire-Code                                              Fire-Code
        """
        )
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock(return_value=expected_output)
        assert switch.get_fec("Ethernet3/1") == FecMode.FC_FEC.value

    def test_configure_vlan(self, switch, mocker):
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock()
        switch.configure_vlan(
            ports="Et3/1",
            vlan=11,
            vlan_type="tagged",
            mode="trunk",
            override_allowed=False,
        )
        assert switch._connection.send_command_list.call_args.args == (
            [
                "configure terminal",
                "vlan 11",
                "exit",
                "interface Et3/1",
                "switchport",
                "switchport trunk allowed vlan add 11",
                "switchport mode trunk",
                "spanning-tree portfast trunk",
                "no shutdown",
            ],
        )
        switch.configure_vlan(
            ports="Et32/1",
            vlan=22,
            vlan_type="tagged",
            mode="trunk",
            override_allowed=True,
        )
        assert switch._connection.send_command_list.call_args.args == (
            [
                "configure terminal",
                "vlan 22",
                "exit",
                "interface Et32/1",
                "switchport",
                "switchport trunk allowed vlan 22",
                "switchport mode trunk",
                "spanning-tree portfast trunk",
                "no shutdown",
            ],
        )
        assert switch._connection.send_command_list.call_count == 2

    def test_show_vlans(self, switch, mocker):
        expected_output = dedent(
            """
        VLAN  Name                             Status    Ports
        ----- -------------------------------- --------- -------------------------------
        1     default                          active    Et2/1, Et3/1, Et4/1, Et5/1
                                                         Et6/1, Et7/1, Et8/1, Et9/1
                                                         Et32/1
        123   VLAN0123                         active    Et2/1, Et32/1
        """
        )
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=expected_output)
        assert switch.show_vlans(vlans=(1, 123)) == expected_output
        assert switch._connection.send_command.call_args.args == ("show vlan 1,123",)
        switch.show_vlans()
        assert switch._connection.send_command.call_args.args == ("show vlan",)
        assert switch._connection.send_command.call_count == 2

    def test__validate_port_channel_no(self, switch):
        for pc_no in (1, 2000):
            assert switch._validate_port_channel_no(pc_no) is None

        for pc_no in (0, 2001, "x"):
            with raises(ValueError, match="Port channel interface number should be integer in range 1-2000"):
                switch._validate_port_channel_no(pc_no)

    def test_create_port_channel_interface(self, switch, mocker):
        pc_no = 1024
        mocker.patch("mfd_switchmanagement.vendors.arista.base.Arista._validate_port_channel_no")

        switch.create_port_channel_interface(pc_no)
        commands = ["configure terminal", f"interface port-channel {pc_no}", "end"]
        assert switch._validate_port_channel_no.called is True
        switch._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_remove_port(self, switch, mocker):
        port = "port-channel 82"
        mocker.patch("mfd_switchmanagement.vendors.arista.base.Arista._validate_port_and_port_channel_syntax")

        commands = ["configure terminal", f"no interface {port}", "end"]
        switch.remove_port(port)
        assert switch._validate_port_and_port_channel_syntax.called is True
        switch._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_add_port_to_channel_group(self, switch, mocker):
        port = "Ethernet 15/1"
        pc_no = 1555
        modes = ("active", "on", "passive")
        unsupported_mode = "x"
        mocker.patch("mfd_switchmanagement.vendors.arista.base.Arista._validate_port_channel_no")
        mocker.patch("mfd_switchmanagement.vendors.arista.base.Arista._validate_port_and_port_channel_syntax")

        with raises(ValueError, match=f"{unsupported_mode} is incorrect parameter for channel-group mode"):
            switch.add_port_to_channel_group(port, pc_no, mode=unsupported_mode)

        for mode in modes:
            commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no} mode {mode}", "end"]
            switch.add_port_to_channel_group(port, pc_no, mode=mode)
            switch._connection.send_command_list.assert_has_calls([mocker.call(commands)])
            assert switch._validate_port_channel_no.called is True
            assert switch._validate_port_and_port_channel_syntax.called is True

    def test_remove_port_from_port_channel(self, switch, mocker):
        mocker.patch("mfd_switchmanagement.vendors.arista.base.Arista._prepare_port_configuration")
        switch.remove_port_from_port_channel("Et12/1")
        assert switch._prepare_port_configuration.called is True
        switch._connection.send_command_list.assert_has_calls([mocker.call(["no channel-group", "end"])])

    def test_show_port_channel(self, switch, mocker):
        expected_output = dedent(
            """
        Port Channel Port-Channel111:
          No Active Ports
        Port Channel Port-Channel222:
          No Active Ports
        """
        )
        invalid_port_channel_list = (
            "port-channe",
            "port-channel ",
            "port-channel111,222",
            "port-channel, 111,222",
            "port-channel ,111,222",
            "port-channel 111,222,",
        )
        valid_port_channel_list = (
            "port-channel",
            "port-channel 111,222",
            "port-channel 111, 222",
            "port-channel 111,    222",
            "port-channel    111,222",
            "port-channel     111,    222",
            "pOrT-cHaNnEl",
        )
        switch._connection.send_command = mocker.Mock(return_value=expected_output)
        for inv_p_ch in invalid_port_channel_list:
            with pytest.raises(ValueError, match=f"Port is not in port-channel syntax! {inv_p_ch}"):
                switch.show_port_channel(inv_p_ch)
        for v_p_ch in valid_port_channel_list:
            output = switch.show_port_channel(v_p_ch)
        assert output == expected_output

    def test_shutdown(self, switch, mocker):
        switch.send_command_list = mocker.Mock()
        switch.shutdown(shutdown=True, port="Et11/3/0")
        switch._connection.send_command_list.assert_called_once_with(
            ["configure terminal", "interface Et11/3/0", "shutdown"]
        )
        switch.shutdown(shutdown=False, port="Et11/3/0")
        switch._connection.send_command_list.assert_called_with(
            ["configure terminal", "interface Et11/3/0", "no shutdown"]
        )

    def test_enable_port(self, switch, mocker):
        switch.send_command_list = mocker.Mock()
        switch.enable_port(port="Et11/3/0", count=2)
        assert 2 == switch._connection.send_command_list.call_count

    def test_disable_port(self, switch, mocker):
        switch.disable_port(port="Et11/3/0", count=5)
        switch._connection.send_command_list.assert_called_with(
            ["configure terminal", "interface Et11/3/0", "shutdown"]
        )
        assert switch._connection.send_command_list.call_count == 5

    def test_show_port_running_config(self, switch, mocker):
        expected_output = dedent(
            """
        interface Ethernet15/1
            dcbx mode ieee
            speed forced 100gfull
            switchport trunk allowed vlan 100
            spanning-tree portfast
        """
        )
        switch._connection.send_command = mocker.Mock(return_value=expected_output)
        output = switch.show_port_running_config(port="Et15/1")
        switch._connection.send_command.assert_called_with("show running-config interfaces Et15/1")
        assert output == expected_output

    def test_is_port_linkup(self, switch, mocker):
        portup = "Ethernet15/1       Up     linkUp   linkUp                     0:42:01 ago"
        portdown = "Ethernet15/1       Up     linkDown linkDown                   0:42:01 ago"
        unknown = "% Invalid input"
        switch._connection.send_command = mocker.Mock()
        switch._connection.send_command.return_value = portup
        assert switch.is_port_linkup(port="Et15/1") is True
        switch._connection.send_command.return_value = portdown
        assert switch.is_port_linkup(port="Et15/1") is False
        switch._connection.send_command.return_value = unknown
        with pytest.raises(SwitchException, match="Link status parsing error on: Arista; interface: Et15/1"):
            switch.is_port_linkup(port="Et15/1")

    def test_configure_dcbx(self, switch, mocker):
        mocker.patch.object(switch, "configure_dcbx_qos_map")
        mocker.patch.object(switch, "configure_dcbx_ets_traffic_class")

        switch.configure_dcbx()

        switch.configure_dcbx_qos_map.assert_called_once_with({3: 1})
        switch.configure_dcbx_ets_traffic_class.assert_called_once_with({1: 100})

    def test_configure_lldp(self, switch):
        switch.configure_lldp("Et1/1")

        switch._connection.send_configuration.assert_called_with(
            [
                "interface Et1/1",
                "lldp transmit",
                "lldp receive",
            ]
        )

    def test_configure_trunking(self, switch):
        switch.configure_trunking("Et1/1")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Et1/1",
                "switchport mode trunk",
                "switchport trunk allowed vlan all",
            ]
        )

    def test_configure_dcbx_mode(self, switch):
        switch.configure_dcbx_mode("Et1/1")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Et1/1",
                "dcbx mode ieee",
            ]
        )

    def test_disable_flowcontrol(self, switch):
        switch.disable_flowcontrol("Et1/1")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Et1/1",
                "flowcontrol send off",
                "flowcontrol receive off",
            ]
        )

    def test_configure_priority_flow_control(self, switch):
        switch.configure_priority_flow_control("Et1/1")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Et1/1",
                "priority-flow-control mode on",
                "priority-flow-control on",
                "priority-flow-control priority 3 no-drop",
                "priority-flow-control priority 0 no-drop",
                "priority-flow-control priority 1 no-drop",
                "priority-flow-control priority 2 no-drop",
                "priority-flow-control priority 4 no-drop",
                "priority-flow-control priority 5 no-drop",
                "priority-flow-control priority 6 no-drop",
            ]
        )

    def test_configure_pfc(self, switch, mocker):
        mocker.patch.object(switch, "configure_dcbx")
        mocker.patch.object(switch, "configure_lldp")
        mocker.patch.object(switch, "configure_trunking")
        mocker.patch.object(switch, "configure_dcbx_mode")
        mocker.patch.object(switch, "disable_flowcontrol")
        mocker.patch.object(switch, "configure_priority_flow_control")

        switch.configure_pfc_userspace("Et1/1")

        switch.configure_dcbx.assert_called_once()
        switch.configure_lldp.assert_called_once_with("Et1/1")
        switch.configure_trunking.assert_called_once_with("Et1/1")
        switch.configure_dcbx_mode.assert_called_once_with("Et1/1")
        switch.disable_flowcontrol.assert_called_once_with("Et1/1")
        switch.configure_priority_flow_control.assert_called_once_with("Et1/1")

    def test_configure_dcbx_qos_map(self, switch, mocker):
        switch._connection.send_configuration = mocker.Mock()
        switch.configure_dcbx_qos_map({3: 1})
        switch._connection.send_configuration.assert_called_once_with(
            [
                "dcbx ets qos map cos 3 traffic-class 1",
            ]
        )

    def test_configure_dcbx_ets_traffic_class(self, switch, mocker):
        switch._connection.send_configuration = mocker.Mock()
        switch.configure_dcbx_ets_traffic_class({1: 100})
        switch._connection.send_configuration.assert_called_once_with(
            [
                "dcbx ets traffic-class 1 bandwidth 100",
            ]
        )

    def test_disable_pfc_userspace(self, switch, mocker):
        port = "ethernet 1/1"

        # Mock dependencies
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        switch._connection.send_configuration = mocker.Mock()
        switch.configure_dcbx_ets_traffic_class = mocker.Mock()
        switch.configure_dcbx_qos_map = mocker.Mock()

        # Call the method
        switch.disable_pfc_userspace(port)

        # Assertions
        switch._validate_port_and_port_channel_syntax.assert_called_once_with(ethernet_port=port)
        switch._connection.send_configuration.assert_any_call([f"default interface {port}"])
        switch.configure_dcbx_ets_traffic_class.assert_called_once_with(class_bandwidth={1: 100}, disable=True)
        switch.configure_dcbx_qos_map.assert_called_once_with(cos_to_tc_map={3: 1}, disable=True)
