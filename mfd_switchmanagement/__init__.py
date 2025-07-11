# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for switch management."""

# connections
from .connections.ssh import SSHSwitchConnection

# api connections
from .connections.vendors.cisco_api import CiscoAPIConnection
from .vendors.arista.arista_7050 import Arista7050
from .vendors.arista.base import Arista
from .vendors.brocade.base import Fabos
from .vendors.cisco.base import Cisco
from .vendors.cisco.nx_os import Cisco_NXOS
from .vendors.cisco.os_4000 import CiscoOS4000
from .vendors.cisco.os_6500 import CiscoOS6500
from .vendors.dell.dell_os9 import DellOS9
from .vendors.dell.dell_os10 import DellOS10
from .vendors.dell.dell_os9 import DellOS9_7000
from .vendors.dell.dell_os9 import DellOS9_8132
from .vendors.dell.dell_os9 import DellOS9_Force10
from .vendors.dell.dell_os9 import DellOS9_S4128
from .vendors.dell.dell_os9 import DellOS9_S5048
from .vendors.extreme.base import Extreme
from .vendors.extreme.extreme_exos import ExtremeExos
from .vendors.ibm.base import IBM
from .vendors.junos.base import Junos
from .vendors.mellanox.base import Mellanox
from .vendors.mellanox.mellanox_25G import Mellanox25G
from .vendors.ovs.base import Ovs
