# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from pytest import fixture, raises, mark

from mfd_switchmanagement import Cisco_NXOS, CiscoAPIConnection, SSHSwitchConnection
from mfd_switchmanagement.exceptions import SwitchWaitForHoldingLinkStateTimeout, SwitchException

show_mac_address_table_address_console_empty = dedent(
    """\
Legend:
        * - primary entry, G - Gateway MAC, (R) - Routed MAC, O - Overlay MAC
        age - seconds since last seen,+ - primary entry using vPC Peer-Link,
        (T) - True, (F) - False, C - ControlPlane MAC, ~ - vsan
   VLAN     MAC Address      Type      age     Secure NTFY Ports
---------+-----------------+--------+---------+------+----+------------------"""
)
show_mac_address_table_address_console = dedent(
    """\
Legend:
        * - primary entry, G - Gateway MAC, (R) - Routed MAC, O - Overlay MAC
        age - seconds since last seen,+ - primary entry using vPC Peer-Link,
        (T) - True, (F) - False, C - ControlPlane MAC, ~ - vsan
   VLAN     MAC Address      Type      age     Secure NTFY Ports
---------+-----------------+--------+---------+------+----+------------------
*    1     0050.566e.db34   dynamic  0         F      F    Eth1/49"""
)
show_mac_address_table_address = [
    {
        "jsonrpc": "2.0",
        "result": {
            "body": {
                "TABLE_mac_address": {
                    "ROW_mac_address": {
                        "disp_mac_addr": "0050.5663.b4d8",
                        "disp_type": "* ",
                        "disp_vlan": "144",
                        "disp_is_static": "disabled",
                        "disp_age": "0",
                        "disp_is_secure": "disabled",
                        "disp_is_ntfy": "disabled",
                        "disp_port": "Ethernet1/5/2",
                    }
                }
            }
        },
        "id": 1,
    }
]
api_response_not_found_input_item = [
    {
        "jsonrpc": "2.0",
        "result": None,
        "id": 1,
    }
]


def show_interface_ethernet_table(state):
    return [
        {
            "jsonrpc": "2.0",
            "result": {
                "body": {
                    "TABLE_interface": {
                        "ROW_interface": {
                            "interface": "Ethernet1/1/1",
                            "vlan": "100",
                            "type": "eth",
                            "portmode": "trunk",
                            "state": f"{state}",
                            "state_rsn_desc": "Administratively down",
                            "speed": "auto",
                            "ratemode": "D",
                        }
                    }
                }
            },
            "id": 1,
        }
    ]


class TestCiscoNX:
    """Class for CiscoNX tests."""

    @fixture
    def switch_console(self, mocker) -> Cisco_NXOS:
        switch = Cisco_NXOS.__new__(Cisco_NXOS)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        switch._connection = mocker.create_autospec(SSHSwitchConnection, autospec=True)
        return switch

    @fixture
    def switch_api(self, mocker) -> Cisco_NXOS:
        switch = Cisco_NXOS.__new__(Cisco_NXOS)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        switch._connection = mocker.create_autospec(CiscoAPIConnection, autospec=True)
        return switch

    def test_get_port_by_mac_pass_console(self, switch_console):
        mac = "00:AA:BB:CC:DD:EE"
        switch_console._connection.send_command.return_value = show_mac_address_table_address_console
        assert switch_console.get_port_by_mac(mac=mac) == "Eth1/49"

    def test_get_port_by_mac_not_found_mac_console(self, switch_console):
        mac = "00:AA:BB:CC:EE:DD"
        switch_console._connection.send_command.return_value = show_mac_address_table_address_console_empty
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.eedd on address-table."):
            switch_console.get_port_by_mac(mac=mac)

    def test_get_port_by_mac_empty_outputs_console(self, switch_console):
        switch_console._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.bbcc on address-table."):
            switch_console.get_port_by_mac(mac="00:AA:BB:CC:BB:CC")

    def test_get_vlan_by_mac_pass_console(self, switch_console):
        mac = "00:AA:BB:CC:DD:EE"
        switch_console._connection.send_command.return_value = show_mac_address_table_address_console
        assert switch_console.get_vlan_by_mac(mac=mac) == 1

    def test_get_vlan_by_mac_not_found_mac_console(self, switch_console):
        mac = "00:AA:BB:CC:EE:DD"
        switch_console._connection.send_command.return_value = show_mac_address_table_address_console_empty
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.eedd on address-table."):
            switch_console.get_vlan_by_mac(mac=mac)

    def test_get_vlan_by_mac_empty_outputs_console(self, switch_console):
        switch_console._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.bbcc on address-table."):
            switch_console.get_vlan_by_mac(mac="00:AA:BB:CC:BB:CC")

    def test_get_port_by_mac_pass(self, switch_api):
        mac = "00:AA:BB:CC:EE:DD"
        switch_api._connection.send_command.return_value = show_mac_address_table_address
        assert switch_api.get_port_by_mac(mac=mac) == "Ethernet1/5/2"

    def test_get_port_by_mac_not_found_mac(self, switch_api):
        mac = "00:AA:BB:CC:EE:DD"
        switch_api._connection.send_command.return_value = api_response_not_found_input_item
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.eedd on address-table."):
            switch_api.get_port_by_mac(mac=mac)

    def test_get_port_by_mac_empty_outputs(self, switch_api):
        switch_api._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.bbcc on address-table."):
            switch_api.get_port_by_mac(mac="00:AA:BB:CC:BB:CC")

    def test_get_vlan_by_mac_pass(self, switch_api):
        mac = "00:AA:BB:CC:EE:DD"
        switch_api._connection.send_command.return_value = show_mac_address_table_address
        assert switch_api.get_vlan_by_mac(mac=mac) == 144

    def test_get_vlan_by_mac_not_found_mac(self, switch_api):
        mac = "00:AA:BB:CC:EE:DD"
        switch_api._connection.send_command.return_value = api_response_not_found_input_item
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.eedd on address-table."):
            switch_api.get_vlan_by_mac(mac=mac)

    def test_get_vlan_by_mac_empty_outputs(self, switch_api):
        switch_api._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find MAC address 00aa.bbcc.bbcc on address-table."):
            switch_api.get_vlan_by_mac(mac="00:AA:BB:CC:BB:CC")

    def test_delete_port_bw_by_tc(self, switch_console, mocker):
        port = "eth2/12"
        suffix = "A"

        switch_console.delete_port_bw_by_tc(port=port, suffix=suffix)

        switch_console._connection.send_command_list.assert_has_calls(
            [
                mocker.call(
                    [
                        "configure terminal",
                        f"interface {port}",
                        f"no service-policy type qos input QOS_{suffix}",
                        f"no service-policy type queuing input IN_{suffix}",
                    ]
                )
            ],
            any_order=False,
        )

    def test_create_qos_policy(self, switch_console, mocker):
        bw = [80, 20, 0, 0, 0, 0, 0, 0]
        up2tc = [0, 0, 0, 1, 0, 0, 0, 0]
        switch_console.create_qos_policy(bandwidth=bw, up2tc=up2tc, suffix="A")

        switch_console._connection.send_command_list.assert_has_calls(
            [
                mocker.call(
                    [
                        "configure terminal",
                        "policy-map type queuing IN_A",
                        "class type queuing c-in-q-default",
                        "bandwidth percent 80",
                        "class type queuing c-in-q1",
                        "bandwidth percent 20",
                    ]
                ),
                mocker.call(
                    [
                        "configure terminal",
                        "class-map type qos match-all TC0_A",
                        "match cos 0,1,2,4,5,6,7",
                        "class-map type qos match-all TC1_A",
                        "match cos 3",
                    ]
                ),
                mocker.call(
                    [
                        "configure terminal",
                        "policy-map type qos QOS_A",
                        "class TC0_A",
                        "set qos-group 0",
                        "class TC1_A",
                        "set qos-group 1",
                    ]
                ),
            ],
            any_order=False,
        )

    def test_show_port_dcbx(self, switch_console):
        port = "eth2/12"
        switch_console.show_port_dcbx(port=port)

        switch_console._connection.send_command.assert_called_with(f"show lldp dcbx interface {port}")

    def test_set_port_pfc_by_tc_success(self, switch_console, mocker):
        port = "eth2/12"
        pfc = "on"
        switch_console.set_port_pfc_by_tc(port=port, qos_priority=1, pfc=pfc)

        switch_console._connection.send_command_list.assert_has_calls(
            [mocker.call(["configure terminal", f"interface {port}", f"priority-flow-control mode {pfc}"])],
            any_order=False,
        )

    def test_set_port_pfc_by_tc_invalid_pfc(self, switch_console):
        port = "eth2/12"
        pfc = "up"
        with raises(ValueError):
            switch_console.set_port_pfc_by_tc(port=port, qos_priority=1, pfc=pfc)

    def test_set_port_bw_by_tc(self, switch_console, mocker):
        port = "eth2/12"
        suffix = "A"
        switch_console.set_port_bw_by_tc(port=port, suffix=suffix)

        switch_console._connection.send_command_list.assert_has_calls(
            [
                mocker.call(
                    [
                        "configure terminal",
                        f"interface {port}",
                        f"service-policy type qos input QOS_{suffix}",
                        f"service-policy type queuing input IN_{suffix}",
                    ]
                )
            ],
            any_order=False,
        )

    def test_delete_qos_policy(self, switch_console, mocker):
        suffix = "A"
        switch_console.delete_qos_policy(suffix=suffix)

        commands = [
            "configure terminal",
            f"no policy-map type qos QOS_{suffix}",
            f"no policy-map type queuing IN_{suffix}",
        ]
        for i in Cisco_NXOS.QOS_PRIORITY:
            commands.append(f"no class-map type qos match-all TC{i}_{suffix}")

        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)], any_order=False)

    def test_wait_for_holding_link_state_unexpected_state(self, switch_console, mocker):
        switch_console.is_port_linkup = mocker.Mock(return_value=False)
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.sleep")
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.TimeoutCounter")
        with raises(SwitchWaitForHoldingLinkStateTimeout):
            switch_console._wait_for_holding_link_state(port="eth2/2", link_up=True, timeout=3)

    def test_wait_for_holding_link_state_link_flap(self, switch_console, mocker):
        switch_console.is_port_linkup = mocker.Mock(side_effect=[False, True, False, True, False, True])
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.sleep", autospec=True, spec_set=True)
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.TimeoutCounter", autospec=True, spec_set=True)
        with raises(SwitchWaitForHoldingLinkStateTimeout):
            switch_console._wait_for_holding_link_state(port="eth2/2", link_up=True, timeout=2)

    def test_wait_for_holding_link_state_success(self, switch_console, mocker):
        switch_console.is_port_linkup = mocker.Mock(side_effect=[True, True, True, True, True, True])
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.sleep", autospec=True, spec_set=True)
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.TimeoutCounter", side_effect=[False, True])
        switch_console._wait_for_holding_link_state(port="eth2/2", link_up=True, timeout=2)

    def test_wait_for_holding_link_state_expected_state(self, switch_console, mocker):
        switch_console.is_port_linkup = mocker.Mock(side_effect=[False, True, False, False, False, False])
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.sleep")
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.TimeoutCounter", side_effect=[False, False, True])
        switch_console._wait_for_holding_link_state(port="eth2/2", link_up=False, timeout=2)

    def test_clear_port_dcbx(self, switch_console, mocker):
        switch_console._validate_configure_parameters = mocker.Mock()
        switch_console.shutdown = mocker.Mock()
        switch_console._wait_for_holding_link_state = mocker.Mock()
        switch_console.shutdown = mocker.Mock()
        switch_console._wait_for_holding_link_state = mocker.Mock()
        port = "eth2/2"
        commands = [
            "configure terminal",
            f"interface {port}",
            "no lldp dcbx version cee",
            "no lldp dcbx version ieee",
        ]
        switch_console.clear_port_dcbx(port=port)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)], any_order=False)

    def test_set_port_dcbx_version(self, switch_console, mocker):
        switch_console._validate_configure_parameters = mocker.Mock()
        switch_console.shutdown = mocker.Mock()
        switch_console._wait_for_holding_link_state = mocker.Mock()
        switch_console.shutdown = mocker.Mock()
        switch_console._wait_for_holding_link_state = mocker.Mock()
        port = "eth2/2"
        mode = "cee"
        commands = ["configure terminal", f"interface {port}", f"lldp dcbx version {mode}"]
        switch_console.set_port_dcbx_version(port=port, mode=mode)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)], any_order=False)

    def test_is_port_linkup_both_states(self, switch_api):
        switch_api._connection.send_command.return_value = show_interface_ethernet_table("up")
        assert switch_api.is_port_linkup("Ethernet1/1/1") is True

        switch_api._connection.send_command.return_value = show_interface_ethernet_table("down")
        assert switch_api.is_port_linkup("Ethernet1/1/1") is False

    def test_is_port_linkup_empty_output(self, switch_api):
        switch_api._connection.send_command.return_value = ""
        with raises(SwitchException, match=r"State of port: Ethernet1\/1\/1 not found, API response may be corrupted."):
            switch_api.is_port_linkup("Ethernet1/1/1")

    def test_is_port_linkup_unknown_state(self, switch_api):
        switch_api._connection.send_command.return_value = show_interface_ethernet_table("unknown")
        with raises(SwitchException, match=r"Unable to read state of': Cisco_NXOS; interface: Ethernet1\/1\/1"):
            switch_api.is_port_linkup("Ethernet1/1/1")

    def test_is_port_linkup_not_found_port(self, switch_api):
        switch_api._connection.send_command.return_value = api_response_not_found_input_item
        with raises(SwitchException, match=r"Could not find port Ethernet1\/1\/1 in switch interfaces."):
            switch_api.is_port_linkup("Ethernet1/1/1")

    def test_is_port_linkup_parsing_error(self, switch_api):
        switch_api._connection.send_command.return_value = [
            {
                "jsonrpc": "2.0",
                "result": {"body": {}},
                "id": 1,
            }
        ]
        with raises(SwitchException, match=r"Link status parsing error on: Cisco_NXOS; interface: Ethernet1\/1\/1\)"):
            switch_api.is_port_linkup("Ethernet1/1/1")

    def test_is_port_linkup_console(self, switch_console):
        switch_console._connection.send_command.return_value = "down"
        assert switch_console.is_port_linkup("Ethernet1/1/1") is False

    def test__validate_port_channel_no(self, switch_console):
        for pc_no in (1, 4096):
            assert switch_console._validate_port_channel_no(pc_no) is None

        for pc_no in (0, 4097, "x"):
            with raises(ValueError, match="Port channel interface number should be integer in range 1-4096"):
                switch_console._validate_port_channel_no(pc_no)

    def test_create_port_channel_interface(self, switch_console, mocker):
        pc_no = 1024
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.Cisco_NXOS._validate_port_channel_no")

        switch_console.create_port_channel_interface(pc_no)
        commands = ["configure terminal", f"interface port-channel {pc_no}"]
        assert switch_console._validate_port_channel_no.called is True
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_remove_port(self, switch_console, mocker):
        port = "port-channel 82"

        commands = ["configure terminal", f"no interface {port}"]
        switch_console.remove_port(port)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_show_port_channel_summary(self, switch_console, mocker):
        pc_no = 1024

        switch_console.show_port_channel_summary()
        command = "show port-channel summary"
        switch_console._connection.send_command.assert_called_with(command)

        switch_console.show_port_channel_summary(pc_no)
        command = f"show port-channel summary interface port-channel {pc_no}"
        switch_console._connection.send_command.assert_called_with(command)

    @mark.parametrize("tested_port", ["Eth1/1/1", "port-channel 10"])
    def test_set_switchport_mode(self, switch_console, mocker, tested_port):
        port = tested_port
        mode = "trunk"

        with raises(ValueError, match="Incorrect switchport mode"):
            switch_console.set_switchport_mode(port, "not_allowed_mode")

        switch_console.set_switchport_mode(port, mode)
        commands = ["configure terminal", f"interface {port}", f"switchport mode {mode}"]
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_add_port_to_channel_group(self, switch_console, mocker):
        port = "Eth1/1/1"
        pc_no = 1000
        modes = ("active", "on", "passive")
        unsupported_mode = "x"
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.Cisco_NXOS._validate_port_channel_no")
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.Cisco_NXOS._validate_port_and_port_channel_syntax")

        with raises(ValueError, match=f"{unsupported_mode} is incorrect parameter for channel-group mode"):
            switch_console.add_port_to_channel_group(port, pc_no, mode=unsupported_mode)

        commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no}"]
        switch_console.add_port_to_channel_group(port, pc_no)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])
        assert switch_console._validate_port_channel_no.called is True
        assert switch_console._validate_port_and_port_channel_syntax.called is True

        commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no} force"]
        switch_console.add_port_to_channel_group(port, pc_no, force=True)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

        for mode in modes:
            commands = ["configure terminal", f"interface {port}", f"channel-group {pc_no} mode {mode}"]
            switch_console.add_port_to_channel_group(port, pc_no, mode=mode)
            switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_add_port_to_channel_group_unsupported_port_type(self, switch_console):
        unsupported_port = "port-channel 10"
        pc_no = 1000

        with pytest.raises(ValueError, match=f"Port is not in ethernet port syntax! {unsupported_port}"):
            switch_console.add_port_to_channel_group(unsupported_port, pc_no)

    def test_set_lacp_rate(self, switch_console, mocker):
        port = "Eth1/1/1"
        allowed_rates = ["fast", "normal"]
        unsupported_rate = "x"
        mocker.patch("mfd_switchmanagement.vendors.cisco.nx_os.base.Cisco_NXOS._validate_port_and_port_channel_syntax")

        with raises(ValueError, match=f"{unsupported_rate} is incorrect option for LACP rate"):
            switch_console.set_lacp_rate(port, unsupported_rate)

        for rate in allowed_rates:
            commands = ["configure terminal", f"interface {port}", f"lacp rate {rate}"]
            switch_console.set_lacp_rate(port, rate)
            switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])
            assert switch_console._validate_port_and_port_channel_syntax.called is True

    def test_set_lacp_rate_unsuported_port_type(self, switch_console):
        unsupported_port = "port-channel 10"
        with raises(ValueError, match=f"Port is not in ethernet port syntax! {unsupported_port}"):
            switch_console.set_lacp_rate(unsupported_port, "fast")

    def test_disable_lacp_rate(self, switch_console, mocker):
        port = "Eth1/1/1"

        commands = ["configure terminal", f"interface {port}", "no lacp rate"]
        switch_console.disable_lacp_rate(port)
        switch_console._connection.send_command_list.assert_has_calls([mocker.call(commands)])

    def test_disable_lacp_rate_invalid_port_type(self, switch_console):
        port = "port-channel 10"

        with pytest.raises(ValueError, match=f"Port is not in ethernet port syntax! {port}"):
            switch_console.disable_lacp_rate(port)
