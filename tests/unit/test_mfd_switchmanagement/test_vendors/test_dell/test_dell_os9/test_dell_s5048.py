# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest

from mfd_switchmanagement import DellOS9_S5048
from mfd_switchmanagement.exceptions import SwitchException


class TestDellS5048:
    """Class for Dell S5048 tests."""

    @pytest.fixture()
    def switch(self, mocker) -> DellOS9_S5048:
        switch = DellOS9_S5048.__new__(DellOS9_S5048)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    def test_is_port_linkup(self, switch, mocker):
        out = """\
        Port                 Description  Status Speed        Duplex Vlan
        Te 1/4/1                          Up     10000 Mbit   Full   3260"""
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.is_port_linkup("Te 1/4/1") is True
        out = """\
        Port                 Description  Status Speed        Duplex Vlan
        Hu 1/1                            Down   100000 Mbit  Auto   --"""
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.is_port_linkup("Hu 1/1") is False

    def test_is_port_linkup_failure(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value="")
        with pytest.raises(SwitchException):
            switch.is_port_linkup("Te 1/4/1")
