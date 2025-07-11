# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""IBM Base tests."""

import pytest
from pytest import fixture

from mfd_switchmanagement import IBM


class TestIBM:
    """Class for IBM tests."""

    MAXIMUM_FRAME_SIZE = 1

    @fixture
    def switch(self, mocker) -> IBM:
        switch = IBM.__new__(IBM)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

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
        input_mac = "aa-bb-cc-dd-ee-ff"
        expected_mac = "aa:bb:cc:dd:ee:ff"

        result = switch.change_standard_to_switch_mac_address(input_mac)

        # Assert
        assert result == expected_mac
