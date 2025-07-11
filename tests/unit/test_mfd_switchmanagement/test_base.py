# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re

import pytest

from mfd_switchmanagement.base import Switch


class TestBaseSwitch:
    @pytest.fixture
    def switch(self, mocker) -> Switch:
        switch = Switch.__new__(Switch)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)

        return switch

    @pytest.fixture
    def port_regex(self, switch):
        switch.PORT_REGEX = re.compile(
            r"(^((gi|te|fo|tw|tf|fi|hu) (\d+/){1,2}\d+)( - (\d+/)*\d+)?( , "
            r"((gi|te|fo|tw|tf|fi|hu) (\d+/){1,2}\d+)(-(\d+/)*\d+)?)*$|^po\d+$)",
            re.I,
        )

    def test__validate_configure_parameters_no_ports(self, switch):
        with pytest.raises(ValueError):
            switch._validate_configure_parameters(ports=None)

    def test__validate_configure_parameters_only_ports_invalid(self, switch, port_regex):
        ports = "te 0/1/1/1"
        with pytest.raises(ValueError):
            switch._validate_configure_parameters(ports=ports)

    def test__validate_configure_parameters_only_ports_valid(self, switch, port_regex):
        ports = "te 0/1"
        switch._validate_configure_parameters(ports=ports)

    @pytest.mark.parametrize("vlan_type", ["untagged", "tagged"])
    def test__validate_configure_parameters_vlan_type_valid(self, switch, vlan_type, port_regex):
        ports = "te 0/1"
        vlan_type = vlan_type
        switch._validate_configure_parameters(ports=ports, vlan_type=vlan_type)

    @pytest.mark.parametrize("vlan_type", ["untaged", "taged"])
    def test__validate_configure_parameters_vlan_type_invalid(self, switch, vlan_type, port_regex):
        ports = "te 0/1"
        vlan_type = vlan_type
        with pytest.raises(ValueError):
            switch._validate_configure_parameters(ports=ports, vlan_type=vlan_type)

    def test__validate_configure_parameters_mode_valid_trunk(self, switch, port_regex):
        ports = "te 0/1"
        mode = "Trunk"
        switch._validate_configure_parameters(ports=ports, mode=mode)

    def test__validate_configure_parameters_mode_valid_access(self, switch, port_regex):
        ports = "te 0/1"
        mode = "ACCESS"
        switch._validate_configure_parameters(ports=ports, mode=mode, vlan=1)

    def test__validate_configure_parameters_mode_valid_access_no_vlan(self, switch, port_regex):
        ports = "te 0/1"
        mode = "ACCESS"
        with pytest.raises(ValueError):
            switch._validate_configure_parameters(ports=ports, mode=mode)

    @pytest.mark.parametrize("mode", ["access", "trunk"])
    def test__validate_configure_parameters_mode_valid_untagged_invalid(self, switch, mode, port_regex):
        ports = "te 0/1"
        mode = mode
        with pytest.raises(ValueError):
            switch._validate_configure_parameters(ports=ports, mode=mode, vlan_type="untagged")

    @pytest.mark.parametrize("mode", ["access", "trunk"])
    def test__validate_configure_parameters_mode_valid_untagged_valid(self, switch, mode, port_regex):
        ports = "te 0/1"
        mode = mode
        switch._validate_configure_parameters(ports=ports, mode=mode, vlan_type="untagged", vlan=1)
