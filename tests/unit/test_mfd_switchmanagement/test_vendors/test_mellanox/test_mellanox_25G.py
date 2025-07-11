# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from pytest import fixture

from mfd_switchmanagement import Mellanox25G
from mfd_switchmanagement.base import FecMode
from mfd_switchmanagement.exceptions import SwitchException


class TestMellanox25G:
    """Class for Mellanox25G tests."""

    @fixture
    def switch(self, mocker) -> Mellanox25G:
        switch = Mellanox25G.__new__(Mellanox25G)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    def test_set_fec_success(self, switch, mocker):
        port = "Eth1/9/1"
        fec_mode = FecMode.RS_FEC
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock()
        switch._is_fec_mode_set = mocker.Mock(return_value=True)

        assert switch.set_fec(port, fec_mode)
        switch._prepare_port_configuration.assert_called_once_with(port)
        switch._connection.send_command_list.assert_called_once_with(
            ["shutdown", f"fec-override {fec_mode.value}", "no shutdown"]
        )

    def test_set_fec_failure(self, switch, mocker):
        port = "Eth1/9/1"
        fec_mode = FecMode.RS_FEC
        switch._prepare_port_configuration = mocker.Mock()
        switch._connection = mocker.Mock()
        switch._connection.send_command_list = mocker.Mock()
        switch._is_fec_mode_set = mocker.Mock(return_value=False)

        result = switch.set_fec(port, fec_mode)
        assert result is False

    def test_get_fec_success(self, switch, mocker):
        port = "ethernet 1/1"
        expected_fec_mode = FecMode.RS_FEC.value
        port_cfg = """
        interface ethernet 1/1 fec-override rs-fec force
        interface ethernet 1/1 speed 1G force
        interface ethernet 1/1 switchport mode trunk
        interface ethernet 1/1 description TRUNK TO Dell7048
        """
        switch.show_port_running_config = mocker.Mock(return_value=port_cfg)
        assert switch.get_fec(port) == expected_fec_mode
        switch.show_port_running_config.assert_called_once_with(port)

    def test_get_fec_failure(self, switch, mocker):
        port = "ethernet 1/1"
        port_cfg = """
        interface ethernet 1/1 speed 1G force
        interface ethernet 1/1 switchport mode trunk
        interface ethernet 1/1 description TRUNK TO Dell7048
        """
        switch.show_port_running_config = mocker.Mock(return_value=port_cfg)

        with pytest.raises(SwitchException, match=f"Error while checking FEC on port: {port}"):
            switch.get_fec(port)
        switch.show_port_running_config.assert_called_once_with(port)
