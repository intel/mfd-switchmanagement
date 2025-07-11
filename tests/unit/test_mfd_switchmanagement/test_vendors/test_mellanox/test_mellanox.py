# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from pytest import fixture
from textwrap import dedent

from mfd_switchmanagement import Mellanox
from mfd_switchmanagement.data_structures import State, ETSMode
from mfd_switchmanagement.exceptions import SwitchException


class TestMellanox:
    """Class for Mellanox tests."""

    @fixture
    def switch(self, mocker) -> Mellanox:
        switch = Mellanox.__new__(Mellanox)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        switch._connection = mocker.Mock()
        return switch

    def test_get_lldp_neighbors_parser_pass(self, switch, mocker):
        out = """
        --------------------------------------------------------------------------------
        Local Interface      Device ID            Port ID              System Name
        --------------------------------------------------------------------------------
        Eth1/5/1             3c:fd:aa:bb:cc:f0    3c:fd:aa:bb:cc:f0    Not Advertised
        Eth1/5/2             3c:fd:aa:bb:cc:f1    3c:fd:aa:bb:cc:f1    Not Advertised
        Eth1/31              f8:bc:aa:bb:cc:e0    fortyGigE 0/52       LIN-ND3-DS5000
        """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        neighbors = switch.get_lldp_neighbors()
        assert len(neighbors) == 3
        assert neighbors[0].loc_portid == "Eth1/5/1"
        assert neighbors[1].rem_sysname == "Not Advertised"
        assert neighbors[2].rem_devid == "f8:bc:aa:bb:cc:e0"

    def test_get_lldp_neighbors_empty_list(self, switch, mocker):
        out = """
                --------------------------------------------------------------------------------
                Local Interface      Device ID            Port ID              System Name
                --------------------------------------------------------------------------------
                """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        neighbors = switch.get_lldp_neighbors()
        assert len(neighbors) == 0

    def test_get_port_speed(self, switch, mocker):
        out = """
                Port                   Operational state           Speed                  Negotiation
                ----                   -----------------           -----                  -----------
                Eth1/9/1               Up                          25G                     Auto
                """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        speed = switch.get_port_speed("Eth1/9/1")
        assert speed == 25000

    def test_get_port_speed_broken_output(self, switch, mocker):
        out = """
                Port                   Operational state           Speed                  Negotiation
                ----                   -----------------           -----                  -----------
                                    Auto
                """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))

        with pytest.raises(SwitchException, match="Couldn't retrieve port speed for port"):
            switch.get_port_speed("Eth1/2")

    def test_show_port_running_config(self, switch, mocker):
        out = """
        ##
        ## Running database "initial"
        ## Generated at 2005/11/10 12:37:16 +0000
        ## Hostname: switch-c6b558
        ##

        ##
        ## Running-config temporary prefix mode setting
        ##
        no cli default prefix-modes enable

        ##
        ## Interface Ethernet configuration
        ##
           interface ethernet 1/1 fec-override fc-fec force
           interface ethernet 1/1 speed 1G force
           interface ethernet 1/2-1/18 speed 10G force
           interface ethernet 1/1 switchport mode trunk
           interface ethernet 1/1 description TRUNK TO Dell7048
           interface ethernet 1/4 shutdown

        ##
        ## VLAN configuration
        ##
           vlan 123
           vlan 1000
           interface ethernet 1/1 switchport trunk allowed-vlan none
           interface ethernet 1/16 switchport access vlan 1000
           interface ethernet 1/1 switchport trunk allowed-vlan 123

        ##
        ## Other IPv6 configuration
        ##
        no ipv6 enable

        ##
        ## AAA remote server configuration
        ##
        # ldap bind-password ********
        # radius-server key ********
        # tacacs-server key ********

        ##
        ## Network management configuration
        ##
        # web proxy auth basic password ********

        ##
        ## X.509 certificates configuration
        ##
        #
        # Certificate name system-self-signed, ID f3db767072acc4e91a9a9802cd976ad02a5fe0ba
        # (public-cert config omitted since private-key config is hidden)

        ##
        ## Persistent prefix mode setting
        ##
        cli default prefix-modes enable
        """
        expected_output_list = [
            "interface ethernet 1/1 fec-override fc-fec force",
            "interface ethernet 1/1 speed 1G force",
            "interface ethernet 1/1 switchport mode trunk",
            "interface ethernet 1/1 description TRUNK TO Dell7048",
            "interface ethernet 1/1 switchport trunk allowed-vlan none",
            "interface ethernet 1/1 switchport trunk allowed-vlan 123",
        ]
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.show_port_running_config(port="ethernet 1/1") == "\n".join(set(expected_output_list))

    def test_prepare_port_configuration(self, switch, mocker):
        switch._connection.exit_port_configuration = mocker.Mock()
        switch._prepare_port_configuration("Eth1/1")
        switch._connection.exit_port_configuration.assert_called_once()

    @pytest.mark.parametrize(
        "input_mac, expected_mac",
        [
            ("aabbccddeeff", "aa:bb:cc:dd:ee:ff"),  # No separators
            ("AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"),  # Colon-separated
            ("AA-BB-CC-DD-EE-FF", "aa:bb:cc:dd:ee:ff"),  # Hyphen-separated
            ("aa.bb.cc.dd.ee.ff", "aa:bb:cc:dd:ee:ff"),  # Dot-separated
            ("AABB.CCDD.EEFF", "aa:bb:cc:dd:ee:ff"),  # Uppercase dot-separated
        ],
    )
    def test_change_standard_to_switch_mac_address(self, switch, input_mac, expected_mac):
        # Act
        result = switch.change_standard_to_switch_mac_address(input_mac)

        # Assert
        assert result == expected_mac

    def test_set_dcb_qos_conf_valid(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        dcbmap = "dcbmap1"
        dcb_tc_info_list = [("0", "30"), ("1", "40"), ("2", "20")]
        expected_commands = [
            "configure terminal",
            "interface ethernet 1/1",
            "traffic-class 0 dcb ets wrr 30",
            "traffic-class 1 dcb ets wrr 40",
            "traffic-class 2 dcb ets wrr 20",
            "traffic-class 3 dcb ets wrr 2",
            "traffic-class 4 dcb ets wrr 2",
            "traffic-class 5 dcb ets wrr 2",
            "traffic-class 6 dcb ets wrr 2",
            "traffic-class 7 dcb ets wrr 2",
            "exit",
            "exit",
        ]

        # Act
        switch.set_dcb_qos_conf(port, dcbmap, dcb_tc_info_list)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_dcb_qos_conf_exceed_traffic_classes(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        dcbmap = "dcbmap1"
        dcb_tc_info_list = [
            ("0", "30"),
            ("1", "40"),
            ("2", "20"),
            ("3", "10"),
            ("4", "10"),
            ("5", "10"),
            ("6", "10"),
            ("7", "10"),
            ("8", "10"),
        ]

        # Act & Assert
        with pytest.raises(ValueError, match="Mellanox switch supports up to 8 traffic classes."):
            switch.set_dcb_qos_conf(port, dcbmap, dcb_tc_info_list)

    def test_set_dcb_qos_conf_exceed_bandwidth(self, switch):
        # Arrange
        port = "ethernet 1/1"
        dcbmap = "dcbmap1"
        dcb_tc_info_list = [("0", "50"), ("1", "60")]

        # Act & Assert
        with pytest.raises(ValueError, match="Total bandwidth percent cannot be exceed 100."):
            switch.set_dcb_qos_conf(port, dcbmap, dcb_tc_info_list)

    def test_set_dcb_priority_flow_control_valid(self, switch):
        # Arrange
        priority = 3
        state = State.ENABLE
        expected_commands = [
            "configure terminal",
            "dcb priority-flow-control priority 3 enable",
            "exit",
        ]

        # Act
        switch.set_dcb_priority_flow_control(priority, state)

        # Assert
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_dcb_priority_flow_control_invalid_priority(self, switch):
        # Arrange
        priority = 8  # Invalid priority (out of range)
        state = State.ENABLE

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid priority value, must be from 0 - 7"):
            switch.set_dcb_priority_flow_control(priority, state)

    def test_set_dcb_priority_flow_control_invalid_state(self, switch):
        # Arrange
        priority = 3
        state = "INVALID_STATE"  # Invalid state

        # Act & Assert
        with pytest.raises(AttributeError):  # Assuming State is an Enum and invalid state raises AttributeError
            switch.set_dcb_priority_flow_control(priority, state)

    def test_enable_pfc(self, switch):
        # Arrange
        expected_commands = ["configure terminal", "dcb priority-flow-control enable force", "exit"]

        # Act
        switch.enable_pfc()

        # Assert
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_prepare_for_pfc_on_port_valid(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        expected_commands = [
            "configure terminal",
            "interface ethernet 1/1 switchport mode hybrid",
            "interface ethernet 1/1 switchport hybrid allowed-vlan all",
            "interface ethernet 1/1 flowcontrol send off force",
            "interface ethernet 1/1 flowcontrol receive off force",
            "exit",
        ]

        # Act
        switch.prepare_for_pfc_on_port(port)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_prepare_for_pfc_on_port_invalid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.prepare_for_pfc_on_port(port)

    def test_enable_pfc_priority_valid(self, switch):
        # Arrange
        priority = 3
        expected_commands = [
            "configure terminal",
            "dcb priority-flow-control priority 3 enable",
            "exit",
        ]

        # Act
        switch.enable_pfc_priority(priority)

        # Assert
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_enable_pfc_priority_invalid_priority_negative(self, switch):
        # Arrange
        priority = -1  # Invalid priority

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid priority value, must be from 0 - 7"):
            switch.enable_pfc_priority(priority)

    def test_enable_pfc_priority_invalid_priority_out_of_range(self, switch):
        # Arrange
        priority = 8  # Invalid priority

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid priority value, must be from 0 - 7"):
            switch.enable_pfc_priority(priority)

    def test_set_ets_on_port_valid_wrr(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        priority = 3
        mode = ETSMode.WRR
        bandwidth = 50
        expected_commands = ["configure terminal", "interface ethernet 1/1 traffic-class 3 dcb ets wrr 50", "exit"]

        # Act
        switch.set_ets_on_port(port=port, priority=priority, mode=mode, bandwidth=bandwidth)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_ets_on_port_valid_strict(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        priority = 2
        mode = ETSMode.STRICT
        expected_commands = ["configure terminal", "interface ethernet 1/1 traffic-class 2 dcb ets strict", "exit"]

        # Act
        switch.set_ets_on_port(port=port, priority=priority, mode=mode)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_ets_on_port_invalid_port(self, switch, mocker):
        switch._validate_configure_parameters = mocker.Mock()
        # Arrange
        port = "invalid_port"
        priority = 3
        mode = ETSMode.WRR
        bandwidth = 50

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_ets_on_port(port=port, priority=priority, mode=mode, bandwidth=bandwidth)

    def test_set_ets_on_port_invalid_mode(self, switch):
        # Arrange
        port = "ethernet 1/1"
        priority = 3
        mode = "INVALID_MODE"  # Invalid mode
        bandwidth = 50

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid ETS mode: INVALID_MODE. Must be either WRR or STRICT."):
            switch.set_ets_on_port(port=port, priority=priority, mode=mode, bandwidth=bandwidth)

    def test_set_ets_on_port_invalid_bandwidth(self, switch):
        # Arrange
        port = "ethernet 1/1"
        priority = 3
        mode = ETSMode.WRR
        bandwidth = 150  # Invalid bandwidth

        # Act & Assert
        with pytest.raises(ValueError, match="For WRR mode, bandwidth must be specified and between 1 and 100."):
            switch.set_ets_on_port(port=port, priority=priority, mode=mode, bandwidth=bandwidth)

    def test_set_ets_on_port_invalid_priority(self, switch):
        # Arrange
        port = "ethernet 1/1"
        priority = 8  # Invalid priority
        mode = ETSMode.WRR
        bandwidth = 50

        # Act & Assert
        with pytest.raises(ValueError, match="Priority must be between 0 and 7."):
            switch.set_ets_on_port(port=port, priority=priority, mode=mode, bandwidth=bandwidth)

    def test_set_bind_switch_priority_on_port_valid(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        traffic_class = 3
        priorities = [0, 1, 2]
        expected_commands = [
            "configure terminal",
            "interface ethernet 1/1 traffic-class 3 bind switch-priority 0 1 2",
            "exit",
        ]

        # Act
        switch.set_bind_switch_priority_on_port(port=port, traffic_class=traffic_class, priorities=priorities)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_bind_switch_priority_on_port_invalid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "invalid_port"
        traffic_class = 3
        priorities = [0, 1, 2]

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_bind_switch_priority_on_port(port=port, traffic_class=traffic_class, priorities=priorities)

    def test_set_bind_switch_priority_on_port_invalid_traffic_class(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        traffic_class = 8  # Invalid traffic class
        priorities = [0, 1, 2]

        # Act & Assert
        with pytest.raises(ValueError, match="Traffic class must be between 0 and 7."):
            switch.set_bind_switch_priority_on_port(port=port, traffic_class=traffic_class, priorities=priorities)

    def test_set_bind_switch_priority_on_port_invalid_priorities(self, switch):
        # Arrange
        port = "ethernet 1/1"
        traffic_class = 3
        priorities = [0, 1, 8]  # Invalid priority

        # Act & Assert
        with pytest.raises(ValueError, match="All switch priorities must be between 0 and 7."):
            switch.set_bind_switch_priority_on_port(port=port, traffic_class=traffic_class, priorities=priorities)

    def test_set_pfc_on_port_userspace_valid(self, switch, mocker):
        # Arrange
        switch.prepare_for_pfc_on_port = mocker.Mock()
        switch.set_bind_switch_priority_on_port = mocker.Mock()
        switch.set_ets_on_port = mocker.Mock()
        port = "ethernet 1/1"

        # Act
        switch.set_pfc_on_port_userspace(port)

        # Assert
        switch.prepare_for_pfc_on_port.assert_called_once_with(port)
        switch.set_bind_switch_priority_on_port.assert_called_once_with(
            port=port, traffic_class=0, priorities=[0, 1, 2, 3, 4, 5, 6, 7]
        )
        switch.set_ets_on_port.assert_any_call(port=port, priority=0, mode=ETSMode.WRR, bandwidth=100)
        for i in range(1, 8):
            switch.set_ets_on_port.assert_any_call(port=port, priority=i, mode=ETSMode.STRICT)

    def test_set_pfc_on_port_userspace_invalid_port(self, switch, mocker):
        switch._validate_configure_parameters = mocker.Mock()
        switch.set_bind_switch_priority_on_port = mocker.Mock()
        switch.set_ets_on_port = mocker.Mock()
        # Arrange
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_pfc_on_port_userspace(port)

    def test_set_pfc_on_port_ndk_valid(self, switch, mocker):
        # Arrange
        switch.prepare_for_pfc_on_port = mocker.Mock()
        switch.set_bind_switch_priority_on_port = mocker.Mock()
        switch.set_ets_on_port = mocker.Mock()
        switch.set_lldp_transmit = mocker.Mock()
        switch.set_lldp_receive = mocker.Mock()
        port = "ethernet 1/1"

        # Act
        switch.set_pfc_on_port_ndk(port)

        # Assert
        switch.prepare_for_pfc_on_port.assert_called_once_with(port)
        switch.set_bind_switch_priority_on_port.assert_any_call(
            port=port, traffic_class=0, priorities=[0, 1, 2, 4, 5, 6, 7]
        )
        switch.set_bind_switch_priority_on_port.assert_any_call(port=port, traffic_class=1, priorities=[3])
        switch.set_ets_on_port.assert_any_call(port=port, priority=0, mode=ETSMode.WRR, bandwidth=50)
        switch.set_ets_on_port.assert_any_call(port=port, priority=1, mode=ETSMode.WRR, bandwidth=50)
        for i in range(2, 8):
            switch.set_ets_on_port.assert_any_call(port=port, priority=i, mode=ETSMode.STRICT)
        switch.set_lldp_transmit.assert_called_once_with(port)
        switch.set_lldp_receive.assert_called_once_with(port)

    def test_set_pfc_on_port_ndk_invalid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        switch.set_bind_switch_priority_on_port = mocker.Mock()
        switch.set_ets_on_port = mocker.Mock()
        switch.set_lldp_transmit = mocker.Mock()
        switch.set_lldp_receive = mocker.Mock()
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_pfc_on_port_ndk(port)

    def test_set_lldp_transmit_valid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        expected_commands = [
            "configure terminal",
            "interface ethernet 1/1 lldp transmit",
            "exit",
        ]

        # Act
        switch.set_lldp_transmit(port)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_lldp_transmit_invalid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_lldp_transmit(port)

    def test_set_lldp_receive_valid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        expected_commands = [
            "configure terminal",
            "interface ethernet 1/1 lldp receive",
            "exit",
        ]

        # Act
        switch.set_lldp_receive(port)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_set_lldp_receive_invalid_port(self, switch, mocker):
        # Arrange
        switch._validate_configure_parameters = mocker.Mock()
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.set_lldp_receive(port)

    def test_disable_pfc_valid_port(self, switch, mocker):
        # Arrange
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        port = "ethernet 1/1"
        expected_commands = [
            "interface ethernet 1/1 shutdown",
            "interface ethernet 1/1 no dcb-priority-flow-control mode",
            "interface ethernet 1/1 no shutdown",
        ]

        # Act
        switch.disable_pfc_on_port(port)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_command_list.assert_called_once_with(expected_commands)

    def test_disable_pfc_invalid_port(self, switch, mocker):
        # Arrange
        port = "invalid_port"
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch.disable_pfc_on_port(port)

    def test_extract_port_number_valid(self, switch):
        # Arrange
        port = "ethernet 1/1"
        expected_port_number = "1/1"

        # Act
        result = switch._extract_port_number(port)

        # Assert
        assert result == expected_port_number

    def test_extract_port_number_valid_with_subport(self, switch):
        # Arrange
        port = "ethernet 1/1/2"
        expected_port_number = "1/1/2"

        # Act
        result = switch._extract_port_number(port)

        # Assert
        assert result == expected_port_number

    def test_extract_port_number_invalid_format(self, switch):
        # Arrange
        port = "invalid_port"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: invalid_port"):
            switch._extract_port_number(port)

    def test_extract_port_number_empty_string(self, switch):
        # Arrange
        port = ""

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid port format: "):
            switch._extract_port_number(port)

    def test_extract_port_number_case_insensitive(self, switch):
        # Arrange
        port = "ETHERNET 1/1"
        expected_port_number = "1/1"

        # Act
        result = switch._extract_port_number(port)

        # Assert
        assert result == expected_port_number
