# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from mfd_switchmanagement import SSHSwitchConnection, Mellanox

switch_details = {"ip": "10.10.10.10", "username": "user", "use_ssh_key": True, "connection_type": SSHSwitchConnection}

switch = Mellanox(**switch_details)
print(switch.show_version())
switch.disconnect()
