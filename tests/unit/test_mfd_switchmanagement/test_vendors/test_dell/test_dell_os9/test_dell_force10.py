# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from pytest import fixture, mark, raises
from textwrap import dedent

from mfd_switchmanagement import DellOS9_Force10
from mfd_switchmanagement.exceptions import SwitchException


class TestDellForce10:
    """Class for DellForce 10 tests."""

    @fixture
    def switch(self, mocker) -> DellOS9_Force10:
        switch = DellOS9_Force10.__new__(DellOS9_Force10)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    @mark.parametrize("tested_port", ["Te2/1", "2/1", "Eth3"])
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
            [f"interface {port}", f"flowcontrol rx {rx} tx {tx}"]
        )

    @mark.parametrize("tested_port", ["Tw1/41", "Tw 1/42"])
    def test_switchport_name_validation(self, switch, tested_port):
        port = tested_port
        match = switch.PORT_REGEX.search(port)
        assert match is not None

    def test_get_pfc_port_statistics_pass(self, switch, mocker):
        out = """Tf 1/13         P0              1611                    39371414                21888305"""
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=out)
        assert switch.get_pfc_port_statistics(port="Tw 1/13", priority=0) == "1611"

    def test_get_pfc_port_statistics_value_error(self, switch):
        with raises(ValueError):
            switch.get_pfc_port_statistics(port="Tw 1/13", priority="0")

    def test_get_pfc_port_statistics_fail(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value="")
        with raises(SwitchException, match="Could not find port statistics for port  from pfc"):
            switch.get_pfc_port_statistics("", 0)

    def test_get_port_dcb_map_dcb_map_found(self, switch, mocker):
        out = """dcb-map LINUX_ETS"""
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=out)
        assert switch.get_port_dcb_map(port="Tw 1/13") == "LINUX_ETS"

    def test_get_port_dcb_map_dcb_map_switch_exception(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value="")
        with raises(SwitchException):
            switch.get_port_dcb_map(port="Te 1/22")

    def test_get_lldp_neighbors_parser_pass(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """
        Loc PortID   Rem Host Name     Rem Port Id                   Rem Chassis Id
        -------------------------------------------------------------------------

        Te 0/12      foo               3c:fd:fe:aa:bb:cc             3c:fd:fe:aa:bb:cc 
        Fo 0/60      LIN-ND2-C6004     Eth1/12                       b4:e9:b0:cc:bb:aa 
        Ma 0/0       jf3418-1B3-tor    5                             00:04:96:dd:ff:aa 
        """  # noqa W291
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        neighbors = switch.get_lldp_neighbors()
        assert len(neighbors) == 3
        assert neighbors[0].loc_portid == "Te 0/12"
        assert neighbors[1].rem_sysname == "LIN-ND2-C6004"
        assert neighbors[2].rem_devid == "00:04:96:dd:ff:aa"

    def test_get_port_speed(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """
              Port Description Status Speed Duplex Vlan
              Fo 1/22/1 6H-c4-n3 le Up 40000 Mbit Full 1313
              """
        switch._connection.send_command_list = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_speed("Fo 1/22/1") == 40000

    def test_get_port_speed_corrupted_output(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """
              Port Description Status Speed Duplex Vlan
              Fo 1/22/1 6H-c4-n3 le Up 4000
              """
        switch._connection.send_command_list = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Couldn't retrieve port speed for port"):
            switch.get_port_speed("Fo 1/22/1")

    def test_create_qos_conf_on_switch_port(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.create_qos_conf_on_switch_port("te1/2/1")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "interface te1/2/1",
                "mtu 9416",
                "portmode hybrid",
                "switchport",
                "protocol lldp",
                "advertise management-tlv management-address system-capabilities system-description system-name",
            ]
        )

    def test_set_tagged_vlan_on_switch_port(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.set_tagged_vlan_on_switch_port("3260", "te1/2/1")
        switch._connection.send_configuration.assert_called_once_with(["interface vlan 3260", "tagged te1/2/1"])

    def test_remove_qos_conf_on_switch_port(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch.remove_qos_conf_on_switch_port("te1/4/1")
        switch._connection.send_configuration.assert_called_once_with(
            [
                "interface te1/4/1",
                "no protocol lldp",
            ]
        )

    def test_enable_fec(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """ fec enabled """
        switch._connection.send_command_list = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.enable_fec("hundredGigE 1/3") is True
        switch._connection.send_command_list.assert_called_with(
            [
                "fec enable",
                "end",
            ]
        )

    def test_disabling_iscsi_app(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._validate_configure_parameters = mocker.Mock()
        port = "te1/1/1"

        # Act
        switch.disabling_iscsi_app(port)

        # Assert
        switch._validate_configure_parameters.assert_called_once_with(ports=port)
        switch._connection.send_configuration.assert_called_once_with(
            [f"interface {port}", "protocol lldp", "no advertise DCBx-appln-tlv iscsi"]
        )
