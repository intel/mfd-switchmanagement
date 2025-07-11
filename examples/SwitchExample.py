# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from mfd_switchmanagement import SSHSwitchConnection, Cisco_NXOS, Arista

# In this case device_type is not set so autodetect will be performed
switch_details = {
    "ip": "10.10.10.10",
    "username": "root",
    "password": "***",
    "secret": "***",
    "auth_timeout": 60,
    "connection_type": SSHSwitchConnection,
}

# In this case device_type is set so cisco_nxos will be used in established connection
switch_details_2 = {
    "ip": "10.10.10.10",
    "username": "root",
    "password": "***",
    "secret": "***",
    "device_type": "cisco_nxos",
    "auth_timeout": 60,
    "connection_type": SSHSwitchConnection,
}

switch = Cisco_NXOS(**switch_details)
print(switch.is_port_linkup("Te2/1"))
switch.disconnect()

# Example for Arista switch how to enable or disable port on this switch
switch_details_3 = {
    "ip": "10.10.10.10",
    "username": "root",
    "password": "***",
    "secret": "***",
    "device_type": "arista",
    "auth_timeout": 60,
    "connection_type": SSHSwitchConnection,
}
switch = Arista(**switch_details)
print(switch.disable_port(port="Te2/1", count=3))
print(switch.enable_port(port="Te2/1", count=3))
switch.disconnect()
