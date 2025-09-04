# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

from pytest import fixture, raises
from textwrap import dedent

from mfd_switchmanagement import DellOS9
from mfd_switchmanagement.exceptions import SwitchException


class TestDellOS9:
    """Class for DellOS9 tests."""

    @fixture
    def switch(self, mocker) -> DellOS9:
        switch = DellOS9.__new__(DellOS9)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    def test_get_port_by_mac(self, switch, mocker):
        """Test get_port_by_mac method."""
        switch._connection = mocker.Mock()
        out = """
        Codes: *N - VLT Peer Synced MAC
        *I - Internal MAC Address used for Inter Process Communication
        VlanId     Mac Address           Type          Interface        State
         1      aa:bb:cc:dd:ee:ff       Dynamic         Te 0/32         Active
        """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_by_mac("aa:bb:cc:dd:ee:ff") == "Te 0/32"

    def test_get_port_by_mac_not_found(self, switch, mocker):
        """Test get_port_by_mac method when MAC address is not found."""
        switch._connection = mocker.Mock()
        out = """
        Codes: *N - VLT Peer Synced MAC
        *I - Internal MAC Address used for Inter Process Communication
        VlanId     Mac Address           Type          Interface        State
        """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Could not find port for MAC address aa:bb:cc:dd:ee:ff"):
            switch.get_port_by_mac("aa:bb:cc:dd:ee:ff")

    def test_get_port_by_mac_invalid_mac(self, switch):
        """Test get_port_by_mac method with invalid MAC address."""
        with raises(ValueError, match="Incorrect MAC address: ZZ:ZZ:ZZ:ZZ:ZZ:ZZ"):
            switch.get_port_by_mac("ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")
