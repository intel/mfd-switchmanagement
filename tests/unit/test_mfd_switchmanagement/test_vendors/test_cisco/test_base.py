# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest

from mfd_switchmanagement import Cisco


class TestCiscoBaseSwitch:
    @pytest.fixture
    def switch(self, mocker) -> Cisco:
        switch = Cisco.__new__(Cisco)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)

        return switch

    def test__validate_port_and_port_channel_syntax_ethernet_type(self, switch):
        ethernet_port = "GigabitEthernet1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)
        ethernet_port = "TwoGigabitEthernet1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)
        ethernet_port = "FiveGigabitEthernet1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)
        ethernet_port = "TenGigabitEthernet1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)
        ethernet_port = "TwentyFiveGigE1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)
        ethernet_port = "FortyGigabitEthernet1/1-1"
        switch._validate_port_and_port_channel_syntax(ethernet_port=ethernet_port)

    def test__validate_port_and_port_channel_syntax_port_channel_type(self, switch):
        port_channel = "port-channel 10"
        switch._validate_port_and_port_channel_syntax(port_channel=port_channel)

    def test__validate_port_and_port_channel_syntax_both(self, switch):
        port = "port-channel 10"
        switch._validate_port_and_port_channel_syntax(both_syntax=port)

    def test__validate_port_and_port_channel_syntax_ethernet_type_but_port_channel_given(self, switch):
        port = "port-channel 10"
        with pytest.raises(ValueError, match=f"Port is not in ethernet port syntax! {port}"):
            switch._validate_port_and_port_channel_syntax(ethernet_port=port)

    def test__validate_port_and_port_channel_syntax_port_channel_type_but_ethernet_given(self, switch):
        port = "TenGigabitEthernet1/1-1"
        with pytest.raises(ValueError, match=f"Port is not in port-channel syntax! {port}"):
            switch._validate_port_and_port_channel_syntax(port_channel=port)

    def test__validate_port_and_port_channel_both_type_but_invalid_given(self, switch):
        invalid_port = "invalid_port"
        with pytest.raises(
            ValueError, match=f"Port is not either in ethernet port or port-channel syntax! {invalid_port}"
        ):
            switch._validate_port_and_port_channel_syntax(both_syntax=invalid_port)

    def test_show_lldp_info(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.show_lldp_info("Eth1/1")
        switch._connection.send_command.assert_called_with("show lldp neighbors interface Eth1/1 detail")

    def test_disable_cdp(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.disable_cdp()
        switch._connection.send_configuration.assert_called_with(["no cdp enable"])

    def test_configure_lldp_receive(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.configure_lldp("Eth1/1", "receive")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Eth1/1",
                "lldp receive",
            ]
        )

    def test_configure_lldp_transmit(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.configure_lldp("Eth1/1", "transmit")
        switch._connection.send_configuration.assert_called_with(
            [
                "interface Eth1/1",
                "lldp transmit",
            ]
        )

    def test_configure_lldp_invalid_param(self, switch):
        with pytest.raises(ValueError, match="Invalid parameter: invalid. Valid values are 'receive' or 'transmit'."):
            switch.configure_lldp("1/1", "invalid")

    def test_get_vlan_by_mac(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.side_effect = [
            "% Invalid input detected at '^' marker.",
            dedent(
                """
                Mac Address Table
            -------------------------------------------

            Vlan    Mac Address       Type        Ports
            ----    -----------       --------    -----
               1    0000.00c9.a000    DYNAMIC     Te1/0/9"""
            ),
        ]
        assert switch.get_vlan_by_mac("00:00:00:C9:A0:00") == 1
        switch._connection.send_command.assert_called_with("sh mac address-table address 0000.00c9.a000")

    def test_get_port_by_mac(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.side_effect = [
            "% Invalid input detected at '^' marker.",
            dedent(
                """
                Mac Address Table
            -------------------------------------------

            Vlan    Mac Address       Type        Ports
            ----    -----------       --------    -----
               1    0000.00c9.a000    DYNAMIC     Te1/0/9"""
            ),
        ]
        assert switch.get_port_by_mac("00:00:00:C9:A0:00") == "Te1/0/9"
        switch._connection.send_command.assert_called_with("sh mac address-table address 0000.00c9.a000")
