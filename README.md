> [!IMPORTANT]  
> This project is under development. All source code and features on the main branch are for the purpose of testing or evaluation and not production ready.

# SwitchManagement
Module for handling operations on switches from different vendors (for example IBM, Cisco, Dell)

___
## Parameters
 `ip: str` - IP Address of switch

 `username: str ` - Username for connection with switch

 `password: str` - Password for connection with switch

 `secret: str` - Secret password for connection with switch uses for enable option, optional if the same as password, it co-work with ssh_key, cannot be replaced by ssh_key usage

 `connection_type: SupportedSwitchConnection` - Type of connection, default SSH

 `use_ssh_key: bool` - Flag to use SSH keys for connection

 `ssh_key_file: Union[str, Path]` - Path to ssh key, if not passed, going to use system ssh keys

 `auth_timeout: int/float` - Timeout in seconds for authentication
 
 `device_type: str` - Device type from Netmiko SSH_MAPPER_BASE, if not passed autodetect will be performed

 `topology: SwitchModel` - Reference to Pydantic model from pytest-mfd-config, from which Switch is created

`global_delay_factor: Optional[int]` - Multiplication factor affecting Netmiko delays (Netmiko default: `1`).
                                       If not set, `2` will be set for connection creation time and `1` after it.
                                       You should consider of increasing this value if your switch is pretty slow to give it a time to properly read output.

 Parameters can be given as kwargs
 ___

## Available connection types

    SSHSwitchConnection
    CiscoAPIConnection

___

## Available device types from Netmiko
    extreme_exos
    alcatel_aos
    alcatel_sros
    apresia_aeos
    arista_eos
    cisco_asa
    cisco_ios
    cisco_nxos
    cisco_xr
    dell_force10
    dell_os9
    dell_os10
    dell_powerconnect
    f5_tmsh
    f5_linux
    hp_comware
    huawei
    juniper_junos
    linux
    brocade_netiron
    extreme_slx
    ubiquiti_edgeswitch
    cisco_wlc
    mellanox_mlnxos
    yamaha

### Available FEC Modes

    RS_FEC
    FC_FEC
    NO_FEC

___
### Available generic methods
	show_version(self) -> str:
	"""show switch detailed info for further identification"""

	disconnect(self) -> None:
	"""close connection with switch."""

	show_vlans(self) -> str:
	"""show all ports vlan configuration"""

	show_ports_status(self) -> str:
	"""show all ports status"""

	enable_spanning_tree(self, port: str) -> str:
	"""enable spanning tree on given port"""

	is_mac_address(self, address: str) -> bool:
	"""check correctness of mac address"""

	is_wwn_address(self, address: str) -> bool:
	"""check correctness of wwn address"""

	disable_spanning_tree(self, port: str) -> str:
	"""disable spanning tree on given port"""

	shutdown(self, shutdown: bool, port: str) -> None:
	"""turn switch port on/off"""

	enable_port(self, port: str, count: int = 1) -> None:
	"""enable port on switch"""

	disable_port(self, port: str, count: int = 1) -> None:
	"""disable port on switch"""

	change_vlan(self, port: str, vlan: int) -> str:
	"""change Vlan port and switches mode to access"""

	exit_user(self) -> None:
	"""exit to user mode"""

	set_trunking_interface(self, port: str, vlan: int) -> str:
	"""change mode to trunk on port and allows vlan traffic on this port"""

	show_port_running_config(self, port: str) -> str:
	"""show running config on given port"""

	is_port_linkup(self, port: str) -> bool:
	"""check port link up"""

	set_fec(self, port: str, fec_mode: FecMode) -> None:
	"""set Forward error correction on port"""

	get_fec(self, port: str) -> str:
	"""get Forward error correction on port"""

	disable_jumbo_frame(self, port: str) -> None:
	"""disable MTU on port(s) (restore to default value)"""

	default_ports(self, ports: str) -> None:
	"""set ports to default configuration"""

	enable_jumbo_frame(self, frame_size: int, port: str) -> None:
	"""set MTU on port(s)"""

	enable_max_jumbo(self, port: str) -> None:
	"""set max available MTU on port(s)"""

	get_port_by_mac(self, mac: str) -> Optional[str]:
	"""get port with the specified MAC address"""

	get_lldp_port(self, mac: str) -> str:
	"""get the lldp port with the specified MAC address"""

	get_port_dcbx_version(self, port: str) -> str:
	"""get dcbx version of switch port"""

	set_dcb_qos_conf(self, port: str, dcb_map: str, dcb_tc_info_list: List) -> None:
	"""configure DCB traffic on the switch port"""

	get_dcb_bw_by_up(self, port: str, dcb_map: str, up: int) -> str:
	"""get bandwidth of DCB traffic class from the switch port"""

	get_dcb_tc_by_up(self, port: str, dcb_map: str, up: int) -> str:
	"""retrieve traffic class by user priority for given port or dcb_map"""

	set_port_dcbx_version(self, port: str, mode: str) -> None:
	"""set the DCBX version for the switch port"""

	get_port_dcb_map(self, port: str) -> str:
	"""get the DCB MAP name applied to a given switch port"""

	set_port_dcb_map(self, port: str, dcbmap: str) -> None:
	"""set the DCB MAP for a switch port to a given name"""

	set_dcb_map_tc(self, dcbmap: str, tc: int, bw: int, pfc: str) -> None:
	"""configure a DCB MAP with TC, BW and PFC settings"""

	set_dcb_map_up(self, dcbmap: str, up: str) -> None:
	"""set a User Priority Group on a DCB MAP"""

	delete_dcb_map(self, port: str, dcbmap: str) -> None:
	"""delete a given DCB-MAP from the switch port and switch config"""

	get_dcb_map_bw_by_tc(self, dcbmap: str, tc: int) -> str:
	"""get the bandwidth percentage of traffic class in DCB MAP"""

	get_dcb_map_pfc_by_tc(self, dcbmap: str, tc: int) -> str:
	"""get the PFC state of traffic class in DCB MAP"""

	get_dcb_map_pfc(self, dcbmap: str) -> str:
	"""get the global PFC state for a given DCB MAP"""

	get_tc_by_up(self, up: int) -> int:
	"""retrieve traffic class by user priority for given port"""

	change_standard_to_switch_mac_address(self, address: str) -> str:
	"""convert standard mac address to switch mac address format"""

	change_switch_to_linux_mac_address(self, address: str) -> str:
	"""convert switch mac address to linux mac address format"""

	change_standard_to_switch_IPv4_address(self, address: str) -> str:
	"""convert standard IP address to switch IP address format"""

	change_standard_to_switch_IPv6_address(self, address: str) -> str:
	"""convert standard IP address to switch IP address format"""

	change_switch_to_standard_IPv4_address(self, address: str) -> str:
	"""convert switch IP address to standard IP address format"""

	change_switch_to_standard_ipv6_address(self, address: str) -> str:
	"""convert switch IP address to standard IP address format"""

	get_vlan_by_mac(self, mac: str) -> Optional[int]:
	"""get VLAN of port with the specified MAC address"""

	canonicalize_chassis_id_tlv(self, tlv: str) -> Optional[str]:
	"""convert tlv to correct format"""

	canonicalize_port_id_tlv(self, tlv: str) -> str:
	"""convert tlv to correct format"""

	get_lldp_neighbors(self) -> List[LLDPlink]:
	"""get the lldp neighbors for switch"""

	LLDPlink is a dataclass for local/remote LLDP link pair representation with fields:
	loc_portid: str
    rem_portid: str
    rem_devid: str
    rem_sysname: str

    remove_qos_conf_on_switch_port(self, port: str) -> None:
    """Destroy DCB configuration on the switch-port"""
    create_qos_conf_on_switch_port(self, vlan: str, port: str) -> None:
    """Create DCB configuration on the switch-port with tag vlan."""

## Special switch type

    Open vSwitch
Open vSwitch is a software implementation of a network switch, designed to be used in a virtualized server environment. 
It allows you to set up a network environment that is decoupled from the physical network hardware, providing a high degree of flexibility and control.
The Ovs package exposes a different set of APIs due to the unique nature of Open vSwitch. Despite its software-based operation, 
Open vSwitch shares many characteristics with hardware switches, which is why its support is included in this module alongside 
hardware switches. 

### Available methods

    vsctl_show(self, bridge: str | None = None) -> str:
    """Display an overview of the configuration of Open vSwitch."""

    dpctl_show(self, bridge: str) -> str:
        """Display an overview of the current configuration of the Open vSwitch datapath for selected bridge."""

    ofctl_show(self, bridge: str | None = None) -> str:
        """Display detailed information about the Open vSwitch bridge."""

    add_bridge(self, name: str) -> None:
        """Add bridge with given name."""

    del_bridge(self, name: str) -> None:
        """Delete bridge with given name."""

    add_port_vxlan_type(self, bridge: str, port: str, local_ip: str, remote_ip: str, dst_port: int) -> None:
        """Add vxlan port to the Open vSwitch bridge."""

    add_p4_device(self, pr4_id: int) -> None:
        """Add P4 device."""

    add_bridge_p4(self, bridge: str, p4_id: int) -> None:
        """Add bridge p4 type."""

    del_port(self, bridge: str, port: str) -> None:
        """Delete given port from the bridge."""

    get_version(self) -> str:
        """Get version of OvS."""

    set_vlan_tag(self, interface: str, vlan: str) -> None:
        """Set VLAN tag on the interface."""

    set_vlan_trunk(self, interface: str, vlans: list[str]) -> None:
        """Set multiple VLAN tags on the interface (trunk)."""

    del_flows(self, bridge: str, port_name: str) -> None:
        """Delete OpenFlow rules (flows) from an Open vSwitch bridge that match input port."""

    dpctl_dump_flows(self, bridge: str | None = None) -> str:
        """Display the flow installed on the Open vSwitch bridge."""

    ofctl_dump_flows(self, bridge: str) -> str:
        """Display OpenFlow flows for specific bridge."""

    dump_port(self, bridge: str) -> str:
        """Display information about the datapath ports on the Open vSwitch bridge."""

    set_other_configs(self, commands: list[str]) -> None:
        """Set other_configs params using ovs-vsctl set command."""

___
## Usage
```python
from mfd_switchmanagement import Cisco, SSHSwitchConnection
    cisco =
    {
        'ip'             : '10.10.10.10',
        'username'       : 'root',
        'password'       : "***",
        'secret'         : "***",
        'connection_type': SSHSwitchConnection,
    }

switch = Cisco(**cisco)

print(switch.show_ports_status())
"""
    Port    Name               Status       Vlan       Duplex  Speed Type

    Te2/1   "TRUNK "       connected    trunk         full    10G 10Gbase-LR
    Te2/2   "TRUNK VM"   connected    trunk         full    10G 10Gbase-LR
    Te2/3   10G Windows 2008 i notconnect   119           full    10G 10Gbase-LR
    Te2/4   "Blank for future  notconnect   107           full    10G 10Gbase-LR
    (...)
"""
switch.disconnect()
```
## Available switch types
    Arista
    Arista7050
    Cisco
    Cisco NX-OS (Nexus)
    Cisco IOS 4000
    Cisco IOS 6500
    Fabos
    generic DellOS10
    generic DellOS9
    DellOS9 7000 series
    DellOS9 7048
    DellOS9 8132
    DellOS9 Force10 series
    DellOS9 S4128
    DellOS9 S5048
    Extreme
    ExtremeExos
    Junos
    IBM
    Mellanox
    Mellanox25G

## Special switch type
    Open vSwitch

## Supported switch OSes from Netmiko

    Arista EOS
    Brocade NetIron
    Cisco ASA
    Cisco IOS
    Cisco NX-OS
    Cisco XR
    Dell OS 10
    Dell OS 9
    Extreme SLX-OS
    ExtremeXOS
    JUNOS OS
    Mellanox MLNXOS - Onyx

## Cisco API

for SSL usage you need to pass `ssl_cert: str` parameter with path to certificate file, `ssl_key: str` with path to key file and `verify: bool` parameter, which is set to `False` by default.

## Issue reporting

If you encounter any bugs or have suggestions for improvements, you're welcome to contribute directly or open an issue [here](https://github.com/intel/mfd-switchmanagement/issues).