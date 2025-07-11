# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from pytest import fixture, raises, mark
from textwrap import dedent

from mfd_switchmanagement import Extreme
from mfd_switchmanagement.exceptions import SwitchException

show_vlan_port = """Untagged ports auto-move: On
-----------------------------------------------------------------------------------------------
Name            VID  Protocol Addr       Flags                         Proto  Ports  Virtual
                                                                              Active router
                                                                              /Total
-----------------------------------------------------------------------------------------------
Default         1    --------------------------------T---------------- ANY    46/104 VR-Default
TestTestTestTestTestTestTestTest 100  ------------------------------------------------- ANY    1 /1   VR-Default
-----------------------------------------------------------------------------------------------
Flags : (B) BFD Enabled, (c) 802.1ad customer VLAN, (C) EAPS Control VLAN,
        (d) Dynamically created VLAN, (D) VLAN Admin Disabled,
        (e) CES Configured, (E) ESRP Enabled, (f) IP Forwarding Enabled,
        (F) Learning Disabled, (h) TRILL Enabled, (i) ISIS Enabled,
        (I) Inter-Switch Connection VLAN for MLAG, (k) PTP Configured,
        (l) MPLS Enabled, (L) Loopback Enabled, (m) IPmc Forwarding Enabled,
        (M) Translation Member VLAN or Subscriber VLAN, (n) IP Multinetting Enabled,
        (N) Network Login VLAN, (o) OSPF Enabled, (O) Flooding Disabled,
        (p) PIM Enabled, (P) EAPS protected VLAN, (r) RIP Enabled,
        (R) Sub-VLAN IP Range Configured, (s) Sub-VLAN, (S) Super-VLAN,
        (t) Translation VLAN or Network VLAN, (T) Member of STP Domain,
        (v) VRRP Enabled, (V) VPLS Enabled, (W) VPWS Enabled, (Z) OpenFlow Enabled

Total number of VLAN(s) : 3 (2 displayed)"""

show_fdb_mac = """Mac                     Vlan       Age  Flags         Port / Virtual Port List
------------------------------------------------------------------------------
00:aa:bb:cc:d9:b9    Default(0001) 0015 d m            49

Flags : d - Dynamic, s - Static, p - Permanent, n - NetLogin, m - MAC, i - IP,
        x - IPX, l - lockdown MAC, L - lockdown-timeout MAC, M- Mirror, B - Egress Blackhole,
        b - Ingress Blackhole, v - MAC-Based VLAN, P - Private VLAN, T - VLAN translation,
        D - drop packet, h - Hardware Aging, o - IEEE 802.1ah Backbone MAC,
        S - Software Controlled Deletion, r - MSRP,
        R - TRILL Rbridge, Z - OpenFlow

Total: 46 Static: 0  Perm: 0  Dyn: 46  Dropped: 0  Locked: 0  Locked with Timeout: 0
FDB Aging time: 300"""

show_lldp_neighbors = """Port     Neighbor Chassis ID        Neighbor Port ID           TTL     Age
=============================================================================
1        F8:BC:AA:BB:CC:00          F8:BC:AA:BB:CC:00          121     8
2        F8:BC:AA:BB:CC:02          F8:BC:AA:BB:CC:02          121     8
3        F8:BC:AA:BB:CC:04          F8:BC:AA:BB:CC:04          121     8
4        F8:BC:AA:BB:CC:06          F8:BC:AA:BB:CC:06          121     8
=============================================================================
NOTE: The Chassis ID and/or Port ID might be truncated to fit the screen."""

show_port_information_detail = """Port:   1
Virtual-router: VR-Default
Type:           Q+CR4_3m (Unlicensed)
Random Early drop:      Unsupported
Admin state:    Enabled with  10G full-duplex
Link State:     Active, 10Gbps, full-duplex
Link Ups:       201      Last: Tue Nov 15 12:21:20 2016
Link Downs:     201      Last: Tue Nov 15 12:21:16 2016

VLAN cfg:
         Name: VLAN-ML, Internal Tag = 100, MAC-limit = No-limit, Virtual router:   VR-Default
STP cfg:

Protocol:
         Name: VLAN-ML      Protocol: ANY      Match all protocols.
Trunking:       Load sharing is not enabled.

EDP:            Enabled

ELSM:           Disabled
Ethernet OAM:           Disabled
Learning:       Enabled
Unicast Flooding:       Enabled
Multicast Flooding:     Enabled
Broadcast Flooding:     Enabled
Jumbo:  Enabled, MTU= 9216
Flow Control:   Rx-Pause: Enabled       Tx-Pause: Disabled
Priority Flow Control: Disabled
Reflective Relay:       Disabled
Link up/down SNMP trap filter setting:  Enabled
Egress Port Rate:       No-limit
Broadcast Rate:         No-limit
Multicast Rate:         No-limit
Unknown Dest Mac Rate:  No-limit
QoS Profile:    None configured
Ingress Rate Shaping :          Unsupported
Ingress IPTOS Examination:      Disabled
Ingress 802.1p Examination:     Enabled
Ingress 802.1p Inner Exam:      Disabled
Egress IPTOS Replacement:       Disabled
Egress 802.1p Replacement:      Disabled
NetLogin:                       Disabled
NetLogin port mode:             Port based VLANs
Smart redundancy:               Enabled
Software redundant port:        Disabled
IPFIX:   Disabled               Metering:  Ingress, All Packets, All Traffic
        IPv4 Flow Key Mask:     SIP: 255.255.255.255            DIP: 255.255.255.255
        IPv6 Flow Key Mask:     SIP: ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
                                DIP: ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff

Far-End-Fault-Indication:       Disabled
Shared packet buffer:           default
VMAN CEP egress filtering:      Disabled
Isolation:                      Off
PTP Configured:                 Disabled
Time-Stamping Mode:             None
Configured Port Partition:      4x10G
Current Port Partition:         4x10G
Synchronous Ethernet:           Unsupported
Dynamic VLAN Uplink:            Disabled
VM Tracking Dynamic VLANs:      Disabled"""


class TestExtreme:
    """Class for Extreme tests."""

    MAXIMUM_FRAME_SIZE = 1

    @fixture
    def switch(self, mocker) -> Extreme:
        switch = Extreme.__new__(Extreme)
        switch.__init__ = mocker.create_autospec(switch.__init__, return_value=None)
        return switch

    def test_default_ports_pass(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.return_value = show_vlan_port
        switch.default_ports(ports="2")
        assert switch._connection.send_command.call_count == 6

    def test_default_ports_empty_vlan_output(self, switch, mocker):
        port = "2"
        switch._connection = mocker.Mock()
        switch._connection.send_command.return_value = ""
        switch.default_ports(ports=port)
        assert switch._connection.send_command.call_count == 4

    def test_get_vlan_by_mac(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.side_effect = [
            "",
            show_fdb_mac,
            show_lldp_neighbors,
            show_port_information_detail,
        ]
        assert switch.get_vlan_by_mac(mac="f8:bc:aa:bb:cc:00") == 100

    def test_get_vlan_by_mac_empty_outputs(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find VLAN for MAC address f8:bc:aa:bb:cc:00"):
            switch.get_vlan_by_mac(mac="f8:bc:aa:bb:cc:00")

    def test_get_vlan_by_mac_wrong_mac(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.return_value = ""
        with raises(ValueError):
            switch.get_vlan_by_mac(mac="")

    def test_get_port_by_mac_empty_outputs(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.return_value = ""
        with raises(SwitchException, match="Could not find port for MAC address f8:bc:aa:bb:cc:00"):
            switch.get_port_by_mac(mac="f8:bc:aa:bb:cc:00")

    def test_get_port_by_mac(self, switch, mocker):
        switch._connection = mocker.Mock()
        switch._connection.send_command.side_effect = ["", show_fdb_mac, show_lldp_neighbors]
        assert switch.get_port_by_mac(mac="f8:bc:aa:bb:cc:00") == "1"

    def test_set_port_pfc_by_tc_success(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        qos_priority = 6
        pfc = "on"
        out = "up"
        switch.get_tc_by_up = mocker.Mock(return_value=out)
        switch.set_port_pfc_by_tc(port=port, qos_priority=qos_priority, pfc=pfc)

        switch._connection.send_command.assert_has_calls(
            [
                mocker.call(f"disable flow-control tx-pause ports {port}"),
                mocker.call(f"enable flow-control tx-pause priority {qos_priority} port {port}"),
                mocker.call(f"enable flow-control rx-pause qosprofile QP{out} port {port}"),
            ],
            any_order=False,
        )

    def test_set_port_pfc_by_tc_wrong_pfc(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        qos_priority = 6
        pfc = "something"
        with raises(ValueError):
            switch.set_port_pfc_by_tc(port=port, qos_priority=qos_priority, pfc=pfc)

    def test_delete_port_pfc(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        switch.delete_port_pfc(port=port)

        list_of_commands = []
        for i in Extreme.QOS_PRIORITY:
            list_of_commands.append(f"disable flow-control rx-pause qosprofile QP{i + 1} port {port}")
            list_of_commands.append(f"disable flow-control tx-pause priority {i} port {port}")

        switch._connection.send_command.assert_has_calls(
            [
                mocker.call(list_of_commands[0]),
                mocker.call(list_of_commands[1]),
                mocker.call(list_of_commands[2]),
                mocker.call(list_of_commands[3]),
                mocker.call(list_of_commands[4]),
                mocker.call(list_of_commands[5]),
                mocker.call(list_of_commands[6]),
                mocker.call(list_of_commands[7]),
            ],
            any_order=False,
        )

    def test_set_port_bw_by_tc_success(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        bandwidth = [1, 2, 3, 4]
        switch.delete_port_bw_by_tc = mocker.Mock()
        switch.set_port_bw_by_tc(port=port, bandwidth=bandwidth)

        list_of_commands = []
        for i, item in enumerate(bandwidth):
            list_of_commands.append(f"configure qosprofile QP{i + 1} minbw {item} maxbw 100 ports {port}")

        switch._connection.send_command.assert_has_calls(
            [
                mocker.call(list_of_commands[0]),
                mocker.call(list_of_commands[1]),
                mocker.call(list_of_commands[2]),
                mocker.call(list_of_commands[3]),
            ],
            any_order=False,
        )

    def test_set_port_bw_by_tc_too_long_bandwidth(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        bandwidth = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        with raises(ValueError):
            switch.set_port_bw_by_tc(port=port, bandwidth=bandwidth)

    def test_set_port_bw_by_tc_not_int_in_bandwidth(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        bandwidth = ["0", "1", "2"]
        with raises(ValueError):
            switch.set_port_bw_by_tc(port=port, bandwidth=bandwidth)

    def test_set_port_bw_by_tc_exceeded_sum_of_bandwidth(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"
        bandwidth = [10, 50, 100]
        with raises(ValueError):
            switch.set_port_bw_by_tc(port=port, bandwidth=bandwidth)

    def test_delete_port_bw_by_tc(self, switch, mocker):
        switch._connection = mocker.Mock()
        port = "2"

        switch.delete_port_bw_by_tc(port=port)

        list_of_commands = []
        for i in range(Extreme.MAXIMUM_SUPPORT_TRAFFIC_CLASSES):
            list_of_commands.append(f"configure qosprofile QP{i + 1} minbw 0 maxbw 100 ports {port}")

        switch._connection.send_command.assert_has_calls(
            [
                mocker.call(list_of_commands[0]),
                mocker.call(list_of_commands[1]),
                mocker.call(list_of_commands[2]),
                mocker.call(list_of_commands[3]),
                mocker.call(list_of_commands[4]),
                mocker.call(list_of_commands[5]),
                mocker.call(list_of_commands[6]),
                mocker.call(list_of_commands[7]),
            ],
            any_order=False,
        )

    def test_get_port_speed(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """
              Port Summary Monitor                      Wed Jul 14 06:11:51 2021
              Port     Display              VLAN Name           Port  Link  Speed  Duplex
              #        String               (or # VLANs)        State State Actual Actual
              ========================================================================
              17                            (0002)              E     A     100G   FULL
              ========================================================================
                 Port State: D-Disabled, E-Enabled, F-Disabled by link-flap detection,
                             L-Disabled due to licensing
                 Link State: A-Active, R-Ready, NP-Port Not Present, L-Loopback,
                             D-ELSM enabled but not up
                             d-Ethernet OAM enabled but not up
              """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        assert switch.get_port_speed("17") == 100000

    def test_get_port_speed_corrupted_output(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """
              Port Summary Monitor                      Wed Jul 14 06:11:51 2021
              Port     Display              VLAN Name           Port  Link  Speed  Duplex
              #        String               (or # VLANs)        State State Actual Actual
              ======
              ========================================================================
                 Por
                             d-Ethernet OAM enabled but not up
              """
        switch._connection.send_command = mocker.Mock(return_value=dedent(out))
        with raises(SwitchException, match="Couldn't retrieve port speed for port"):
            switch.get_port_speed("17")

    @mark.parametrize("vlan", [0, 1])
    def test_remove_vlan_incorrect_number(self, switch, vlan):
        with raises(ValueError):
            switch.remove_vlan(vlan)

    def test_remove_vlan(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """Untagged ports auto-move: Inform
-----------------------------------------------------------------------------------------------
Name            VID  Protocol Addr       Flags                         Proto  Ports  Virtual
                                                                              Active router
                                                                              /Total
-----------------------------------------------------------------------------------------------
Default         1    ------------------------------------------------  ANY    41/50 VR-Default
Mgmt            4095 1.3.3.1  /19  ----------------------------------  ANY    1 /1   VR-Mgmt
vlan100         100  ------------------------------------------------  ANY    0 /0   VR-Default
VLAN_0010       10   ------------------------------------------------  ANY    0 /0   VR-Default
"""
        switch._connection.send_configuration = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=out)  # error in output means VLAN removed
        assert switch.remove_vlan(3)
        switch._connection.send_configuration.assert_called_with(["delete vlan 3"])
        switch._connection.send_command.assert_called_with("show vlan")

    def test_remove_vlan_not_removed(self, switch, mocker):
        switch._connection = mocker.Mock()
        out = """Untagged ports auto-move: Inform
-----------------------------------------------------------------------------------------------
Name            VID  Protocol Addr       Flags                         Proto  Ports  Virtual
                                                                              Active router
                                                                              /Total
-----------------------------------------------------------------------------------------------
Default         1    ------------------------------------------------  ANY    41/50 VR-Default
Mgmt            4095 1.3.3.1  /19  ----------------------------------  ANY    1 /1   VR-Mgmt
vlan100         100  ------------------------------------------------  ANY    0 /0   VR-Default
VLAN_0010       10   ------------------------------------------------  ANY    0 /0   VR-Default
VLAN_0003       3    ------------------------------------------------  ANY    1 /1   VR-Default
"""
        switch._connection.send_configuration = mocker.Mock()
        switch._connection.send_command = mocker.Mock(return_value=out)
        assert not switch.remove_vlan(3)
        switch._connection.send_configuration.assert_called_with(["delete vlan 3"])
        switch._connection.send_command.assert_called_with("show vlan")

    def test_get_dcb_map_bw_by_tc_success(self, switch, mocker):
        # Arrange
        switch._connection = mocker.Mock()
        port = "1/1"
        tc = 3
        mock_output = "QP3 MinBw = 50"
        switch._connection.send_command = mocker.Mock(return_value=mock_output)
        mocker.patch("mfd_switchmanagement.vendors.extreme.base.any_match", return_value=[("QP3", "MinBw", "=", "50")])

        # Act
        result = switch.get_dcb_map_bw_by_tc(None, tc, port)

        # Assert
        assert result == "50"
        switch._connection.send_command.assert_called_once_with(f"show qosprofile port {port} | grep QP{tc}")

    def test_get_dcb_map_bw_by_tc_no_port(self, switch):
        # Act & Assert
        with pytest.raises(ValueError, match="Need specify port number to get bandwidth by traffic class"):
            switch.get_dcb_map_bw_by_tc(None, 3, None)

    def test_get_dcb_map_bw_by_tc_invalid_tc(self, switch):
        # Arrange
        tc = switch.MAXIMUM_SUPPORT_TRAFFIC_CLASSES  # Invalid TC (exceeds max)

        # Act & Assert
        with pytest.raises(
            ValueError, match=f"Extreme switch supports up to {switch.MAXIMUM_SUPPORT_TRAFFIC_CLASSES} traffic classes."
        ):
            switch.get_dcb_map_bw_by_tc(None, tc, "1/1")

    def test_get_dcb_map_bw_by_tc_switch_exception(self, switch, mocker):
        # Arrange
        switch._connection = mocker.Mock()
        port = "1/1"
        tc = 3
        switch._connection.send_command = mocker.Mock(return_value="")
        mocker.patch("mfd_switchmanagement.vendors.extreme.base.any_match", return_value=[])

        # Act & Assert
        with pytest.raises(SwitchException, match=f"Error retrieving bandwidth percentage for port {port}, PG {tc}"):
            switch.get_dcb_map_bw_by_tc(None, tc, port)
