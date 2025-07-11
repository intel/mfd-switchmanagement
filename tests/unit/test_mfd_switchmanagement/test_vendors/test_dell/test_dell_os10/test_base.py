# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from pytest import fixture, mark, raises
from textwrap import dedent

from mfd_switchmanagement import DellOS10
from mfd_switchmanagement.exceptions import SwitchException
from mfd_switchmanagement.vendors.dell.dell_os10.base import BreakOutMode


class TestDellOS10:
    """Class for DellForce 10 tests."""

    @fixture
    def switch(self, mocker) -> DellOS10:
        switch = DellOS10.__new__(DellOS10)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    def test__port_range(self, switch):
        assert switch._port_range("eth1/1/1") == ""
        assert switch._port_range("Ethernet 1/1/31:1") == ""
        assert switch._port_range("eth1/1/1-1/1/4") == "range "
        assert switch._port_range("eth1/1/1,1/1/31") == "range "

    def test__validate_configure_parameters(self, switch):
        switch._validate_configure_parameters(ports="eth1/1/1:1")
        switch._validate_configure_parameters(ports="eth1/1/1-1/1/4")
        switch._validate_configure_parameters(ports="ethernet 1/1/1:2-1/1/4:4")
        switch._validate_configure_parameters(ports="ethernet 1/1/1:2-1/1/4:4,1/1/16-1/1/20")
        switch._validate_configure_parameters(ports="eth1/1/1,1/1/15,1/1/20")

        with raises(ValueError):
            switch._validate_configure_parameters(ports="3c:fd:fe:aa:bb:cc")
        with raises(ValueError):
            switch._validate_configure_parameters(ports="eth1/1/1:2-eth1/1/4:4")

    @mark.parametrize("tested_port", ["Eth3", "Eth1/1/1", "Eth1/1/1:1"])
    @mark.parametrize("string_value_rx,tested_bool_rx", [("on", True), ("off", False)])
    @mark.parametrize("string_value_tx,tested_bool_tx", [("on", True), ("off", False)])
    def test_set_port_flowcontrol(
        self, switch, mocker, tested_bool_rx, tested_bool_tx, string_value_rx, string_value_tx, tested_port
    ):
        port = tested_port
        rx = string_value_rx
        tx = string_value_tx
        switch._connection = mocker.Mock()
        switch.set_port_flowcontrol(port, tested_bool_rx, tested_bool_tx)
        switch._connection.send_configuration.assert_called_once_with(
            [
                f"interface {port.lower().replace('eth','ethernet')}",
                f"flowcontrol receive {rx}",
                f"flowcontrol transmit {tx}",
            ]
        )

    def test_get_lldp_neighbors_parser_pass(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        Loc PortID          Rem Host Name        Rem Port Id                    Rem Chassis Id
        --------------------------------------------------------------------------------------
        ethernet1/1/3:1     Not Advertised       00:78:57:aa:bb:cc             39373638-3935-5A43-4A39-
        ethernet1/1/31      B-R03-U23-Mellano... Eth1/32                       24:8a:07:bb:cc:aa
        mgmt1/1/1           LAB-7103-B-R04       19                            00:04:96:dd:ff:aa"""
        )
        switch._connection.send_command = mocker.Mock(return_value=out)
        neighbors = switch.get_lldp_neighbors()
        assert len(neighbors) == 2
        assert neighbors[0].loc_portid == "ethernet1/1/31"
        assert neighbors[1].rem_sysname == "LAB-7103-B-R04"
        assert neighbors[1].rem_devid == "00:04:96:dd:ff:aa"

    def test_get_port_speed(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """\
              Ethernet 1/1/3:1 is up, line protocol is up
                Hardware is Eth, address is 4c:76:25:aa:00:bb
                    Current address is 4c:76:25:aa:00:bb
                Pluggable media present, QSFP28 type is QSFP28 4x(25GBASE-CR)-2.0M
                    Wavelength is 64
                Interface index is 47
                Internet address is not set
                Mode of IPv4 Address Assignment: not set
                Interface IPv6 oper status: Disabled
                MTU 1532 bytes, IP MTU 1500 bytes
                LineSpeed 10G, Auto-Negotiation off
                Flowcontrol rx off tx off
                ARP type: ARPA, ARP Timeout: 60"""
        )
        switch._connection.send_command = mocker.Mock(return_value=out)
        assert switch.get_port_speed("Ethernet 1/1/3:1") == 10000

    def test_get_port_speed_corrupted_output(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """\
                     Ethernet 1/1/3:1 is up, line protocol is up
                       Hardware is Eth, address is 4c:76:25:aa:00:bb
                           Current address is 4c:76:25:aa:00:bb
                       Pluggable media present, QSFP28 type is QSFP28 4x(25GBASE-CR)-2.0M
                           Wavelength is 64
                       Interface index is 47
                       Internet address is not set
                       Mode of IPv4 Address Assignment: not set
                       Interface IPv6 oper status: Disabled
                       MTU 1532 bytes, IP MTU 1500 bytes
                       LineSpeed 0, Auto-Negotiation off
                       Flowcontrol rx off tx off
                       ARP type: ARPA, ARP Timeout: 60"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Couldn't retrieve port speed for port"):
            switch.get_port_speed("Ethernet 1/1/3:1")

    def test_list_vlan_id(self, switch, mocker):
        expected = ["vlan1", "vlan2", "vlan3", "vlan4", "vlan5", "vlan6", "vlan7", "vlan8", "vlan9"]
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        interface vlan1
        interface vlan2
        interface vlan3
        interface vlan4
        interface vlan5
        interface vlan6
        interface vlan7
        interface vlan8
        interface vlan9"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert expected == switch.list_vlan_id()

    def test_get_port_by_mac(self, switch, mocker):
        expected = "ethernet1/1/12:1"
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        Codes: pv <vlan-id> - private vlan where the mac is originally learnt
        VlanId        Mac Address         Type        Interface
        1             3c:fd:fe:aa:bb:cc   dynamic     ethernet1/1/12:1"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert expected == switch.get_port_by_mac("3c:fd:fe:aa:bb:cc")

    def test_get_port_by_mac_missing(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        Codes: pv <vlan-id> - private vlan where the mac is originally learnt
        VlanId        Mac Address         Type        Interface"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Could not find port for MAC address 3c:fd:fe:aa:bb:cc"):
            switch.get_port_by_mac("3c:fd:fe:aa:bb:cc")

    @pytest.mark.parametrize("link_status_text, link_status_bool", [("up", True), ("down", False)])
    def test_is_port_linkup(self, switch, mocker, link_status_text, link_status_bool):
        switch._connection = mocker.Mock()
        out = dedent(
            f"""\
        Ethernet 1/1/1:1 is {link_status_text}, line protocol is up
        Hardware is Eth, address is c8:f7:50:ee:aa:00
            Current address is c8:f7:50:ee:aa:00
        Pluggable media present, QSFP28 type is QSFP28 100GBASE-CR4-1.0M
            Wavelength is 38
        Interface index is 73
        Internet address is not set
        Mode of IPv4 Address Assignment: not set
        Interface IPv6 oper status: Disabled
        MTU 9216 bytes, IP MTU 9184 bytes
        LineSpeed 100G, Auto-Negotiation on
        Configured FEC is cl91-rs, Negotiated FEC is cl91-rs
        Flowcontrol rx on tx off
        ARP type: ARPA, ARP Timeout: 60
        Last clearing of "show interface" counters: 19:35:59
        Queuing strategy: fifo
        Input statistics:
             0 packets, 0 octets
             0 64-byte pkts, 0 over 64-byte pkts, 0 over 127-byte pkts
             0 over 255-byte pkts, 0 over 511-byte pkts, 0 over 1023-byte pkts
             0 Multicasts, 0 Broadcasts, 0 Unicasts
             0 runts, 0 giants, 0 throttles
             0 CRC, 0 overrun, 0 discarded
        """
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.is_port_linkup("Ethernet 1/1/1:1") is link_status_bool

    def test_is_port_linkup_failed(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent("""Ethernet1/1/1:1""")
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Link status parsing error on: DellOS10; interface: Ethernet1/1/1:1"):
            switch.is_port_linkup("Ethernet1/1/1:1")

    def test_get_vlan_by_mac(self, switch, mocker):
        expected = 1
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        Codes: pv <vlan-id> - private vlan where the mac is originally learnt
        VlanId        Mac Address         Type        Interface
        1             3c:fd:fe:aa:bb:cc   dynamic     ethernet1/1/12:1"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert expected == switch.get_vlan_by_mac("3c:fd:fe:aa:bb:cc")

    def test_get_vlan_by_mac_missing(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """\
        Codes: pv <vlan-id> - private vlan where the mac is originally learnt
        VlanId        Mac Address         Type        Interface"""
        )
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Could not find VLAN for MAC address 3c:fd:fe:aa:bb:cc"):
            switch.get_vlan_by_mac("3c:fd:fe:aa:bb:cc")

    def test_clear_port_dcbx(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.clear_port_dcbx("Eth1/1/1:1")
        switch._connection.send_configuration.assert_called_once_with(
            ["interface ethernet1/1/1:1", "no dcbx version", "no ets"]
        )

    def test_delete_port_bw_by_tc(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.delete_port_bw_by_tc("Eth1/1/1:1", "050")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "interface ethernet1/1/1:1",
                "no service-policy input type network-qos PMQ_050",
                "no service-policy output type queuing PM_050",
                "no qos-map traffic-class",
                "no trust-map dot1p",
            ]
        )

    def test_delete_port_pfc(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.delete_port_pfc("Eth1/1/1:1")
        switch._connection.send_configuration.assert_called_once_with(
            ["interface ethernet1/1/1:1", "no priority-flow-control"]
        )

    def test_delete_qos_policy(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.delete_qos_policy("050")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "no policy-map type queuing PM_050",
                "no class-map type queuing Q7_050",
                "no class-map type queuing Q6_050",
                "no class-map type queuing Q5_050",
                "no class-map type queuing Q4_050",
                "no class-map type queuing Q3_050",
                "no class-map type queuing Q2_050",
                "no class-map type queuing Q1_050",
                "no class-map type queuing Q0_050",
                "no qos-map traffic-class QM_050",
                "no trust dot1p-map TM_050",
                "no policy-map type network-qos PMQ_050",
                "no class-map type network-qos CMQ_050",
            ]
        )

    def test_create_qos_policy(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_qos_policy([80, 20, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0], "050")
        switch._connection.send_configuration.assert_has_calls(
            [
                mocker.call(
                    ["trust dot1p-map TM_050", "qos-group 0 dot1p 0,1,2,4,5,6,7", "qos-group 1 dot1p 3", "exit"]
                ),
                mocker.call(
                    [
                        "qos-map traffic-class QM_050",
                        "queue 0 qos-group 0 type ucast",
                        "queue 1 qos-group 1 type ucast",
                    ]
                ),
                mocker.call(
                    [
                        "qos-map traffic-class QM_050",
                        "queue 0 qos-group 0 type mcast",
                        "queue 1 qos-group 1 type mcast",
                    ]
                ),
                mocker.call(
                    [
                        "class-map type queuing Q0_050",
                        "match queue 0",
                    ]
                ),
                mocker.call(
                    [
                        "class-map type queuing Q1_050",
                        "match queue 1",
                    ]
                ),
                mocker.call(
                    [
                        "policy-map type queuing PM_050",
                        "class Q0_050",
                        "bandwidth percent 80",
                        "exit",
                        "class Q1_050",
                        "bandwidth percent 20",
                        "exit",
                    ]
                ),
                mocker.call(["class-map type network-qos CMQ_050", "match qos-group 3"]),
                mocker.call(["policy-map type network-qos PMQ_050", "class CMQ_050", "pause", "pfc-cos 3", "exit"]),
            ]
        )

    def test_create_qos_map_queuing(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_qos_class_map(name="QM_050", priority="0,0,0,1,1", class_type="queuing")

        switch._connection.send_configuration.assert_called_once_with(
            [
                "class-map type queuing QM_050",
                "match queue 0,0,0,1,1",
            ]
        )

    def test_create_qos_map_network(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_qos_class_map(name="QM_050", priority="0,0,0,1,1", class_type="network-qos")

        switch._connection.send_configuration.assert_called_once_with(
            [
                "class-map type network-qos QM_050",
                "match qos-group 0,0,0,1,1",
            ]
        )

    def test_create_qos_map_network_invalid_priority_format(self, switch, mocker):
        switch._connection = mocker.Mock()
        with raises(SwitchException):
            switch.create_qos_class_map(name="QM_050", priority="a , a", class_type="network-qos")

    def test_create_qos_class_map_pass(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_qos_map(queues=[0, 0, 0, 1, 0, 0, 0, 0], tc_name="QM_050", queue_type="ucast")

        switch._connection.send_configuration.assert_called_once_with(
            [
                "qos-map traffic-class QM_050",
                "queue 0 qos-group 0 type ucast",
                "queue 1 qos-group 1 type ucast",
            ]
        )

    def test_set_port_bw_by_tc(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.set_port_bw_by_tc("Eth1/1/1:1", suffix="050")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "interface ethernet1/1/1:1",
                "trust-map dot1p TM_050",
                "qos-map traffic-class QM_050",
                "service-policy output type queuing PM_050",
                "service-policy input type network-qos PMQ_050",
            ]
        )

    def test_set_port_pfc_by_tc(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.set_port_pfc_by_tc("Eth1/1/1:1", qos_priority=3, pfc="on")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "interface ethernet1/1/1:1",
                "flowcontrol receive off",
                "flowcontrol transmit off",
                "priority-flow-control mode on",
            ]
        )

    def test_show_port_dcbx(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.show_port_dcbx("Eth1/1/1:1")
        switch._connection.send_command.assert_called_once_with("show lldp dcbx interface ethernet1/1/1:1")

    def test_set_port_dcbx_version(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.set_port_dcbx_version("Eth1/1/1:1", mode="ieee")
        switch._connection.send_configuration.assert_called_with(["interface ethernet1/1/1:1", "dcbx version ieee"])

    def test_set_ets_mode_on(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._set_ets_mode_on("Eth1/1/1:1")
        switch._connection.send_configuration.assert_called_once_with(["interface ethernet1/1/1:1", "ets mode on"])

    def test_set_ets_mode_on_wrong_port(self, switch, mocker):
        switch._connection = mocker.Mock()

        with raises(ValueError):
            switch._set_ets_mode_on("xgfjfffd")

    def test_create_qos_queuing_policy_map(self, switch, mocker):
        switch._connection = mocker.Mock()
        class_bandwidth_dict = {
            "cmap1": 50,
            "cmap2": 50,
        }
        switch.create_qos_queuing_policy_map("SAN_DCB_MAP", class_bandwidth_dict)
        switch._connection.send_configuration.assert_called_once_with(
            [
                "policy-map type queuing SAN_DCB_MAP",
                "class cmap1",
                "bandwidth percent 50",
                "exit",
                "class cmap2",
                "bandwidth percent 50",
                "exit",
            ]
        )

    def test_create_qos_queuing_policy_map_no_sum_up(self, switch, mocker):
        switch._connection = mocker.Mock()
        class_bandwidth_dict = {
            "cmap1": 70,
            "cmap2": 50,
        }
        with raises(ValueError):
            switch.create_qos_queuing_policy_map("SAN_DCB_MAP", class_bandwidth_dict)

    def test_create_network_qos_policy_map(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_network_qos_policy_map("test_policy", ["test_class"], ["1"])
        switch._connection.send_configuration.assert_called_once_with(
            [
                "policy-map type network-qos test_policy",
                "class test_class",
                "pause",
                "pfc-cos 1",
                "exit",
            ]
        )

    def test_create_network_qos_policy_map_different_lengths(self, switch, mocker):
        switch._connection = mocker.Mock()

        with raises(SwitchException):
            switch.create_network_qos_policy_map("test_policy", ["test_class"], ["1", "2"])

    def test_configure_qos_pfc_interface(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.configure_qos_pfc_interface(
            port="Eth1/1/2:3",
            qos_policy="SAN_DCB_MAP",
            traffic_policy="qos_SAN_DCB_MAP",
            trust_policy="trust_SAN_DCB_MAP",
            service_policy="pfc0",
        )
        switch._connection.send_configuration.assert_has_calls(
            [
                mocker.call(
                    [
                        "interface ethernet1/1/2:3",
                        "service-policy output type queuing SAN_DCB_MAP",
                        "qos-map traffic-class qos_SAN_DCB_MAP",
                        "trust-map dot1p trust_SAN_DCB_MAP",
                        "flowcontrol transmit off",
                        "flowcontrol receive off",
                        "service-policy input type network-qos pfc0",
                    ]
                ),
                mocker.call(
                    [
                        "interface ethernet1/1/2:3",
                        "ets mode on",
                    ]
                ),
                mocker.call(
                    [
                        "interface ethernet1/1/2:3",
                        "priority-flow-control mode on",
                        "lldp tlv-select dcbxp-appln iscsi",
                    ]
                ),
            ]
        )

    def test_create_iscsi_policy_map(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_iscsi_policy_map("policy-iscsi")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "policy-map type application policy-iscsi",
                "class class-iscsi",
                "set qos-group 4",
                "set cos 4",
                "exit",
            ]
        )

    def test_get_group_ports(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = dedent(
            """
            hybrid-group        profile       Ports               Mode
            port-group1/1/1     unrestricted  1/1/1               Eth 400g-1x
                                              1/1/2               Eth 400g-1x
            port-group1/1/2     unrestricted  1/1/3               Eth 400g-1x
                                              1/1/4               Eth 400g-1x
            port-group1/1/3     unrestricted  1/1/5               Eth 400g-1x
                                              1/1/6               Eth 400g-1x
            port-group1/1/4     unrestricted  1/1/7               Eth 400g-1x
                                              1/1/8               Eth 400g-1x
            port-group1/1/5     unrestricted  1/1/9               Eth 400g-1x
                                              1/1/10              Eth 400g-1x
            port-group1/1/6     unrestricted  1/1/11              Eth 400g-1x
                                              1/1/12              Eth 400g-1x
            port-group1/1/7     unrestricted  1/1/13              Eth 400g-1x
                                              1/1/14              Eth 400g-1x
            port-group1/1/8     unrestricted  1/1/15              Eth 400g-1x
                                              1/1/16              Eth 400g-1x
            port-group1/1/9     unrestricted  1/1/17              Eth 400g-1x
                                              1/1/18              Eth 400g-1x
            port-group1/1/10    unrestricted  1/1/19              Eth 400g-1x
                                              1/1/20              Eth 400g-1x
            port-group1/1/11    unrestricted  1/1/21              Eth 400g-1x
                                              1/1/22              Eth 25g-4x
            port-group1/1/12    unrestricted  1/1/23              Eth 100g-1x
                                              1/1/24              Eth 100g-1x
            port-group1/1/13    unrestricted  1/1/25              Eth 400g-1x
                                              1/1/26              Eth 25g-4x
            port-group1/1/14    unrestricted  1/1/27              Eth 25g-4x
                                              1/1/28              Eth 25g-4x
            port-group1/1/15    unrestricted  1/1/29              Eth 100g-2x
                                              1/1/30              Eth 100g-2x
            port-group1/1/16    unrestricted  1/1/31              Eth 100g-2x
                                              1/1/32              Eth 100g-2x
            """
        )
        expected_out = {
            "1/1/1": ["1/1/1", "1/1/2"],
            "1/1/2": ["1/1/3", "1/1/4"],
            "1/1/3": ["1/1/5", "1/1/6"],
            "1/1/4": ["1/1/7", "1/1/8"],
            "1/1/5": ["1/1/9", "1/1/10"],
            "1/1/6": ["1/1/11", "1/1/12"],
            "1/1/7": ["1/1/13", "1/1/14"],
            "1/1/8": ["1/1/15", "1/1/16"],
            "1/1/9": ["1/1/17", "1/1/18"],
            "1/1/10": ["1/1/19", "1/1/20"],
            "1/1/11": ["1/1/21", "1/1/22"],
            "1/1/12": ["1/1/23", "1/1/24"],
            "1/1/13": ["1/1/25", "1/1/26"],
            "1/1/14": ["1/1/27", "1/1/28"],
            "1/1/15": ["1/1/29", "1/1/30"],
            "1/1/16": ["1/1/31", "1/1/32"],
        }
        switch._connection.send_command = mocker.Mock(return_value=out)
        assert switch.get_port_groups() == expected_out

    @pytest.mark.parametrize("port, command", [(None, "mode Eth 100g-1x"), ("1/1/2", "port 1/1/2 mode Eth 100g-1x")])
    def test_set_port_group_mode(self, switch, mocker, port, command):
        switch._connection = mocker.Mock()
        commands = [
            "port-group 1/1/1",
            command,
        ]

        switch.set_port_group_mode(port_group="1/1/1", port=port, mode=BreakOutMode.ETH_100G_1x)
        switch._connection.send_configuration.assert_called_once_with(commands)

    def test_show_lldp_info(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.show_lldp_info("Eth1/1/2:3")
        switch._connection.send_command.assert_called_with("show lldp neighbors interface ethernet1/1/2:3 detail")

    def test_configure_lldp_receive(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.configure_lldp("Eth1/1/2:3", "receive")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface ethernet1/1/2:3",
                "lldp receive",
            ]
        )

    def test_configure_lldp_transmit(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.configure_lldp("Eth1/1/2:3", "transmit")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface ethernet1/1/2:3",
                "lldp transmit",
            ]
        )

    def test_configure_lldp_invalid_param(self, switch):
        with pytest.raises(ValueError, match="Invalid parameter: invalid. Valid values are 'receive' or 'transmit'."):
            switch.configure_lldp("Eth1/1/2:3", "invalid")

    def test__convert_port_name(self, switch):
        assert switch._convert_port_name("eth 1/1/5") == "ethernet 1/1/5"
        assert switch._convert_port_name("Eth 1/1/5") == "ethernet 1/1/5"
        assert switch._convert_port_name("Eth1/1/5") == "ethernet1/1/5"
        assert switch._convert_port_name("eth1/1/5") == "ethernet1/1/5"
        assert switch._convert_port_name("Ethernet 1/1/5") == "ethernet 1/1/5"
        assert switch._convert_port_name("Ethernet 1/1/5:2") == "ethernet 1/1/5:2"

    def test_prepare_port_configuration_single_port(self, switch, mocker):
        """Test _prepare_port_configuration with a single port."""
        port = "eth1/1/1"
        switch._port_range = mocker.MagicMock(return_value="")
        switch._convert_port_name = mocker.MagicMock(return_value="ethernet1/1/1")
        switch._connection = mocker.Mock()
        switch._prepare_port_configuration(port)

        switch._connection.send_command_list.assert_called_once_with(["configure terminal", "interface ethernet1/1/1"])

    def test_prepare_port_configuration_port_range(self, switch, mocker):
        """Test _prepare_port_configuration with a port range."""
        port = "eth1/1/1-1/1/2"
        switch._port_range = mocker.MagicMock(return_value="range ")
        switch._convert_port_name = mocker.MagicMock(return_value="ethernet1/1/1-1/1/2")
        switch._connection = mocker.Mock()
        switch._prepare_port_configuration(port)

        switch._connection.send_command_list.assert_called_once_with(
            ["configure terminal", "interface range ethernet1/1/1-1/1/2"]
        )

    def test__convert_port_name_eth_to_ethernet(self, switch):
        # Covers line 144: conversion logic
        assert switch._convert_port_name("eth 1/1/5") == "ethernet 1/1/5"
        assert switch._convert_port_name("eth1/1/5") == "ethernet1/1/5"

    def test__convert_port_name_no_conversion(self, switch):
        # Covers line 154: no conversion needed
        assert switch._convert_port_name("ethernet 1/1/5") == "ethernet 1/1/5"

    def test_remove_vlan_vlan1(self, switch, mocker):
        # Covers line 333: if vlan == 1
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="Should not remove the default VLAN."):
            switch.remove_vlan(1)

    def test_remove_vlan_no_vlan(self, switch, mocker):
        # Covers line 351: elif not vlan
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="VLAN Id must be specified."):
            switch.remove_vlan(None)

    def test_change_standard_to_switch_mac_address(self, switch):
        # Covers line 428: for c in ':.-'
        mac = "3c:fd:fe:aa:bb:cc"
        result = switch.change_standard_to_switch_mac_address(mac)
        assert result == "3c:fd:fe:aa:bb:cc"

    def test_set_switchport_mode(self, switch, mocker):
        # Covers line 812: set_switchport_mode stub
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        switch.set_switchport_mode("eth1/1/1", "access")
        switch._validate_port_and_port_channel_syntax.assert_called_once()

    def test_add_port_to_channel_group(self, switch, mocker):
        # Covers line 829: add_port_to_channel_group stub
        switch._connection = mocker.Mock()
        switch.add_port_to_channel_group("eth1/1/1", 1)

    def test_set_lacp_rate(self, switch, mocker):
        # Covers line 850: set_lacp_rate stub
        switch._connection = mocker.Mock()
        switch.set_lacp_rate("eth1/1/1", "fast")

    def test_disable_lacp_rate(self, switch, mocker):
        # Covers line 864: disable_lacp_rate stub
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="slow is incorrect option for LACP rate"):
            switch.disable_lacp_rate("eth1/1/1", "slow")

    def test_remove_port(self, switch, mocker):
        # Covers line 873: remove_port stub
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="Port is not in port-channel syntax!"):
            switch.remove_port("eth1/1/1")

    def test__convert_port_name_variants(self, switch):
        # Extra coverage for line 144, 154 with mixed case and whitespace
        assert switch._convert_port_name("Eth 1/1/5") == "ethernet 1/1/5"
        assert switch._convert_port_name("ETH1/1/5") == "ethernet1/1/5"
        assert switch._convert_port_name("ethernet1/1/5") == "ethernet1/1/5"

    def test_remove_vlan_zero(self, switch, mocker):
        # Extra coverage for line 351: vlan=0
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="VLAN Id must be specified."):
            switch.remove_vlan(0)

    def test_remove_vlan_empty_string(self, switch, mocker):
        # Extra coverage for line 351: vlan=""
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError, match="VLAN Id must be specified."):
            switch.remove_vlan("")

    def test_change_standard_to_switch_mac_address_all_separators(self, switch):
        # Extra coverage for line 428: all separators
        mac = "3c.fd.fe.aa.bb.cc"
        result = switch.change_standard_to_switch_mac_address(mac)
        assert result == "3c:fd:fe:aa:bb:cc"
        mac = "3c-fd-fe-aa-bb-cc"
        result = switch.change_standard_to_switch_mac_address(mac)
        assert result == "3c:fd:fe:aa:bb:cc"
        mac = "3c.fd-fe:aa.bb-cc"
        result = switch.change_standard_to_switch_mac_address(mac)
        assert result == "3c:fd:fe:aa:bb:cc"

    def test_disable_lacp_rate_invalid(self, switch, mocker):
        # Extra coverage for line 864: another invalid value
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError):
            switch.disable_lacp_rate("eth1/1/1", "foo")

    def test_remove_port_invalid(self, switch, mocker):
        # Extra coverage for line 873: another invalid port
        switch._connection = mocker.Mock()
        with pytest.raises(ValueError):
            switch.remove_port("notaport")

    @pytest.mark.parametrize(
        "ports, vlan, vlan_type, mode, expected_calls",
        [
            # Test access mode
            (
                "eth1/1/1",
                10,
                "tagged",
                "access",
                [
                    (["interface vlan 10"],),
                    (["interface ethernet1/1/1", "no shutdown", "switchport access vlan 10"],),
                    (["interface vlan 10", "no shutdown"],),
                ],
            ),
            # Test trunk mode with untagged vlan_type
            (
                "eth1/1/2",
                20,
                "untagged",
                "trunk",
                [
                    (["interface vlan 20"],),
                    (["interface ethernet1/1/2", "no shutdown", "switchport access vlan 20"],),
                    (["interface vlan 20", "no shutdown"],),
                ],
            ),
            # Test trunk mode with tagged vlan_type
            (
                "eth1/1/3",
                30,
                "tagged",
                "trunk",
                [
                    (["interface vlan 30"],),
                    (
                        [
                            "interface ethernet1/1/3",
                            "no shutdown",
                            "switchport mode trunk",
                            "switchport trunk allowed vlan 30",
                        ],
                    ),
                    (["interface vlan 30", "no shutdown"],),
                ],
            ),
            # Test access mode with extra whitespace/case
            (
                "eth1/1/4",
                40,
                "TAGGED",
                " ACCESS ",
                [
                    (["interface vlan 40"],),
                    (["interface ethernet1/1/4", "no shutdown", "switchport access vlan 40"],),
                    (["interface vlan 40", "no shutdown"],),
                ],
            ),
        ],
    )
    def test_configure_vlan_various_modes(self, switch, mocker, ports, vlan, vlan_type, mode, expected_calls):
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        switch._port_range = mocker.Mock(return_value="")
        switch._convert_port_name = mocker.Mock(return_value=f"ethernet{ports[3:]}")
        switch.configure_vlan(ports, vlan, vlan_type, mode)
        # Check the order and content of send_configuration calls
        actual_calls = switch._connection.send_configuration.call_args_list
        assert len(actual_calls) == 3
        for call, expected in zip(actual_calls, expected_calls):
            assert call.args[0] == expected[0]

    def test_configure_vlan_vlan1_returns_none(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        result = switch.configure_vlan("eth1/1/1", 1, "tagged", "access")
        assert result is None
        switch._validate_configure_parameters.assert_not_called()
        switch._connection.send_configuration.assert_not_called()

    def test_configure_vlan_calls_validate(self, switch, mocker):
        switch._connection = mocker.Mock()
        validate = mocker.Mock()
        switch._validate_configure_parameters = validate
        switch._port_range = mocker.Mock(return_value="")
        switch._convert_port_name = mocker.Mock(return_value="ethernet1/1/1")
        switch.configure_vlan("eth1/1/1", 2, "tagged", "access")
        validate.assert_called_once_with(ports="eth1/1/1", mode="access", vlan=2, vlan_type="tagged")

    def test_configure_vlan_trunk_tagged_range(self, switch, mocker):
        # Test with port range and trunk/tagged
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        switch._port_range = mocker.Mock(return_value="range ")
        switch._convert_port_name = mocker.Mock(return_value="ethernet1/1/1-1/1/4")
        switch.configure_vlan("eth1/1/1-1/1/4", 100, "tagged", "trunk")
        switch._connection.send_configuration.assert_any_call(["interface vlan 100"])
        switch._connection.send_configuration.assert_any_call(
            [
                "interface range ethernet1/1/1-1/1/4",
                "no shutdown",
                "switchport mode trunk",
                "switchport trunk allowed vlan 100",
            ]
        )
        switch._connection.send_configuration.assert_any_call(["interface vlan 100", "no shutdown"])

    def test_show_port_running_config_calls_send_command(self, switch, mocker):
        # Arrange
        port = "Eth1/1/1:1"
        expected_port_name = "ethernet1/1/1:1"
        expected_command = f"show running-configuration interface {expected_port_name}"
        expected_output = "interface ethernet1/1/1:1\n description test"
        switch._connection = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value=expected_port_name)
        switch._connection.send_command = mocker.Mock(return_value=expected_output)

        # Act
        result = switch.show_port_running_config(port)

        # Assert
        switch._convert_port_name.assert_called_once_with(port)
        switch._connection.send_command.assert_called_once_with(expected_command)
        assert result == expected_output

    def test_show_port_running_config_with_different_port_formats(self, switch, mocker):
        # Arrange
        ports = [
            ("eth1/1/2", "ethernet1/1/2"),
            ("Ethernet 1/1/3", "ethernet 1/1/3"),
            ("ETH1/1/4:2", "ethernet1/1/4:2"),
        ]
        for port, expected_port_name in ports:
            expected_command = f"show running-configuration interface {expected_port_name}"
            expected_output = f"interface {expected_port_name}\n description test"
            switch._connection = mocker.Mock()
            switch._convert_port_name = mocker.Mock(return_value=expected_port_name)
            switch._connection.send_command = mocker.Mock(return_value=expected_output)

            # Act
            result = switch.show_port_running_config(port)

            # Assert
            switch._convert_port_name.assert_called_with(port)
            switch._connection.send_command.assert_called_with(expected_command)
            assert result == expected_output

    @pytest.mark.parametrize(
        "port, output, expected",
        [
            # Typical up
            (
                "Ethernet 1/1/1:1",
                "Ethernet 1/1/1:1 is up, line protocol is up\nOther stuff",
                True,
            ),
            # Typical down
            (
                "Ethernet 1/1/1:1",
                "Ethernet 1/1/1:1 is down, line protocol is up\nOther stuff",
                False,
            ),
            # Unknown status (not up/down)
            (
                "Ethernet 1/1/1:1",
                "Ethernet 1/1/1:1 is testing, line protocol is up\nOther stuff",
                None,
            ),
            # Port with different case
            (
                "ethernet1/1/2",
                "ethernet1/1/2 is up, line protocol is up",
                True,
            ),
            # Port with whitespace
            (
                "Ethernet 1/1/3",
                "Ethernet 1/1/3 is down, line protocol is down",
                False,
            ),
        ],
    )
    def test_is_port_linkup_various_statuses(self, switch, mocker, port, output, expected):
        switch._connection = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value=port)
        switch._connection.send_command = mocker.Mock(return_value=output)
        result = switch.is_port_linkup(port)
        assert result is expected

    def test_is_port_linkup_no_match_raises(self, switch, mocker):
        port = "Ethernet1/1/1:1"
        output = "Some unrelated output"
        switch._connection = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value=port)
        switch._connection.send_command = mocker.Mock(return_value=output)
        with pytest.raises(SwitchException, match=f"Link status parsing error on: DellOS10; interface: {port}"):
            switch.is_port_linkup(port)

    def test_is_port_linkup_returns_none_for_unexpected_status(self, switch, mocker):
        port = "Ethernet 1/1/1:1"
        output = "Ethernet 1/1/1:1 is unknown, line protocol is up"
        switch._connection = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value=port)
        switch._connection.send_command = mocker.Mock(return_value=output)
        assert switch.is_port_linkup(port) is None

    @pytest.mark.parametrize("enabled", [True, False])
    def test_set_port_mirroring_valid_enable_disable(self, switch, mocker, enabled):
        # Arrange
        src_port = "Eth1/1/1"
        dst_port = "Eth1/1/2"
        session = "10"
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        switch._convert_port_name = mocker.Mock(
            side_effect=lambda p: "ethernet1/1/1" if p == src_port else "ethernet1/1/2"
        )
        # Patch any_match
        patch_any_match = mocker.patch("mfd_switchmanagement.vendors.dell.dell_os10.base.any_match")
        if enabled:
            # Simulate session does not exist
            patch_any_match.return_value = []
            switch._connection.send_command.return_value = ""
            # Act
            switch.set_port_mirroring(src_port, dst_port, session, enabled)
            # Assert
            switch._validate_configure_parameters.assert_any_call(ports=src_port)
            switch._validate_configure_parameters.assert_any_call(ports=dst_port)
            switch._connection.send_command.assert_called_with('show running-configuration | grep "monitor session"')
            switch._connection.send_configuration.assert_any_call(["interface range vlan 2-4049"])
            switch._connection.send_configuration.assert_any_call(
                ["interface ethernet1/1/2", "no mtu", "no switchport"]
            )
            switch._connection.send_configuration.assert_any_call(
                [
                    "monitor session 10",
                    "source interface ethernet1/1/1 direction rx",
                    "destination interface ethernet1/1/2",
                ]
            )
        else:
            # Simulate session exists
            patch_any_match.return_value = [("monitor session 10",)]
            switch._connection.send_command.return_value = ""
            # Act
            switch.set_port_mirroring(src_port, dst_port, session, enabled)
            # Assert
            switch._validate_configure_parameters.assert_any_call(ports=src_port)
            switch._validate_configure_parameters.assert_any_call(ports=dst_port)
            switch._connection.send_command.assert_called_with('show running-configuration | grep "monitor session"')
            switch._connection.send_configuration.assert_any_call(
                [
                    "no monitor session 10",
                    "interface Eth1/1/2",
                    f"mtu {switch.MAXIMUM_FRAME_SIZE:d}",
                    "switchport mode access",
                ]
            )

    def test_set_port_mirroring_invalid_session_id(self, switch, mocker):
        src_port = "Eth1/1/1"
        dst_port = "Eth1/1/2"
        session = "70000"
        switch._validate_configure_parameters = mocker.Mock()
        with pytest.raises(ValueError, match="Invalid Session ID. Valid Range 0 - 65535"):
            switch.set_port_mirroring(src_port, dst_port, session, True)

    def test_set_port_mirroring_enable_session_already_defined(self, switch, mocker):
        src_port = "Eth1/1/1"
        dst_port = "Eth1/1/2"
        session = "10"
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        switch._convert_port_name = mocker.Mock(
            side_effect=lambda p: "ethernet1/1/1" if p == src_port else "ethernet1/1/2"
        )
        patch_any_match = mocker.patch("mfd_switchmanagement.vendors.dell.dell_os10.base.any_match")
        patch_any_match.return_value = [("monitor session 10",)]
        switch._connection.send_command.return_value = ""
        with pytest.raises(ValueError, match="Session ID Requested to be Added is Already Defined!"):
            switch.set_port_mirroring(src_port, dst_port, session, True)

    def test_set_port_mirroring_disable_session_not_found(self, switch, mocker):
        src_port = "Eth1/1/1"
        dst_port = "Eth1/1/2"
        session = "10"
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        switch._convert_port_name = mocker.Mock(
            side_effect=lambda p: "ethernet1/1/1" if p == src_port else "ethernet1/1/2"
        )
        patch_any_match = mocker.patch("mfd_switchmanagement.vendors.dell.dell_os10.base.any_match")
        patch_any_match.return_value = []
        switch._connection.send_command.return_value = ""
        with pytest.raises(ValueError, match="Session ID Requested to be Removed Cannot Be Found."):
            switch.set_port_mirroring(src_port, dst_port, session, False)

    def test_set_port_mirroring_calls_validate_for_both_ports(self, switch, mocker):
        src_port = "Eth1/1/1"
        dst_port = "Eth1/1/2"
        session = "1"
        switch._connection = mocker.Mock()
        validate = mocker.Mock()
        switch._validate_configure_parameters = validate
        switch._convert_port_name = mocker.Mock(return_value="ethernet1/1/1")
        mocker.patch("mfd_switchmanagement.vendors.dell.dell_os10.base.any_match", return_value=[])
        switch._connection.send_command.return_value = ""
        switch.set_port_mirroring(src_port, dst_port, session, True)
        assert validate.call_count == 2
        validate.assert_any_call(ports=src_port)
        validate.assert_any_call(ports=dst_port)

    @pytest.mark.parametrize(
        "port, lacp_rate",
        [
            ("eth1/1/1", "fast"),
            ("eth1/1/2", "normal"),
            ("Ethernet 1/1/3", "fast"),
            ("ETH1/1/4:2", "normal"),
        ],
    )
    def test_disable_lacp_rate_valid(self, switch, mocker, port, lacp_rate):
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value="ethernet1/1/1")
        switch.disable_lacp_rate(port, lacp_rate)
        switch._validate_port_and_port_channel_syntax.assert_called_once_with(ethernet_port=port)
        switch._convert_port_name.assert_called_once_with(port)
        switch._connection.send_command_list.assert_called_once_with(
            ["configure terminal", "interface ethernet1/1/1", f"no lacp rate {lacp_rate}"]
        )

    @pytest.mark.parametrize("lacp_rate", ["slow", "foo", "", None])
    def test_disable_lacp_rate_invalid_value(self, switch, mocker, lacp_rate):
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        with pytest.raises(ValueError, match="incorrect option for LACP rate"):
            switch.disable_lacp_rate("eth1/1/1", lacp_rate)

    def test_disable_lacp_rate_calls_validate(self, switch, mocker):
        switch._connection = mocker.Mock()
        validate = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = validate
        switch._convert_port_name = mocker.Mock(return_value="ethernet1/1/1")
        switch.disable_lacp_rate("eth1/1/1", "fast")
        validate.assert_called_once_with(ethernet_port="eth1/1/1")

    def test_remove_port_valid_port_channel(self, switch, mocker):
        # Arrange
        port = "port-channel1"
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        switch._convert_port_name = mocker.Mock(return_value="port-channel1")

        # Act
        switch.remove_port(port)

        # Assert
        switch._validate_port_and_port_channel_syntax.assert_called_once_with(port_channel=port)
        switch._convert_port_name.assert_called_once_with(port)
        switch._connection.send_command_list.assert_called_once_with(
            ["configure terminal", "no interface port-channel1"]
        )

    def test_remove_port_invalid_port_raises(self, switch, mocker):
        # Arrange
        port = "eth1/1/1"
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock(
            side_effect=ValueError("Port is not in port-channel syntax!")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Port is not in port-channel syntax!"):
            switch.remove_port(port)
        switch._validate_port_and_port_channel_syntax.assert_called_once_with(port_channel=port)
        switch._connection.send_command_list.assert_not_called()

    def test_remove_port_convert_port_name_called(self, switch, mocker):
        # Arrange
        port = "port-channel10"
        switch._connection = mocker.Mock()
        switch._validate_port_and_port_channel_syntax = mocker.Mock()
        convert_port_name = mocker.Mock(return_value="port-channel10")
        switch._convert_port_name = convert_port_name

        # Act
        switch.remove_port(port)

        # Assert
        convert_port_name.assert_called_once_with(port)
        switch._connection.send_command_list.assert_called_once()
