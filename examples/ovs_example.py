# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

from mfd_connect import RPyCConnection
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.link import LinkState
from mfd_switchmanagement import Ovs
from mfd_switchmanagement.vendors.ovs.base import REVALIDATOR_CMD, HANDLER_CMD

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

conn = RPyCConnection(ip="10.10.10.10")

network_adapters_owner = LinuxNetworkAdapterOwner(connection=conn)
bridge_interface = network_adapters_owner.get_interface(interface_name="br0")

ovs = Ovs(connection=conn)
ovs.add_bridge(bridge_interface.name)

bridge_interface.link.set_link(state=LinkState.UP)

ovs.add_port("br0", "eth1")
ovs.set_other_configs([REVALIDATOR_CMD, HANDLER_CMD])

sw_cfg = ovs.vsctl_show()
logger.info(f"'ovs-vsctl show' output: {sw_cfg}")

bridge_info = ovs.ofctl_show("br0")
logger.info(f"'ovs-ofctl show br0' output: {bridge_info}")
