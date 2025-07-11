# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from netmiko import Netmiko
from mfd_switchmanagement.connections.ssh import SSHSwitchConnection
from mfd_switchmanagement.exceptions import SwitchConnectionException
from mfd_common_libs import log_levels


class TestSSHSwitchConnection:
    @pytest.fixture
    def ssh_connection(self, mocker):
        mocker.patch("mfd_switchmanagement.connections.ssh.SSHSwitchConnection.connect")
        params = {
            "ip": "10.10.10.10",
            "username": "root",
            "password": "***",
            "secret": "***",
            "auth_timeout": 60,
            "connection_type": SSHSwitchConnection,
        }
        ssh_connection = SSHSwitchConnection(**params)
        ssh_connection._connection = mocker.create_autospec(Netmiko)
        mocker.stopall()
        return ssh_connection

    def test__reconnect_connection_success(self, ssh_connection, mocker):
        ssh_connection._connection._open = mocker.Mock()
        ssh_connection._connection.enable = mocker.Mock()
        ssh_connection._check_connection = mocker.Mock(return_value=True)

        ssh_connection._reconnect()

        ssh_connection._connection._open.assert_called_once()
        ssh_connection._connection.enable.assert_called_once()
        ssh_connection._check_connection.assert_called_once()

    def test__reconnect_connection_failed(self, ssh_connection, mocker):
        ssh_connection._connection._open = mocker.Mock()
        ssh_connection._connection.enable = mocker.Mock()
        ssh_connection._check_connection = mocker.Mock(return_value=False)

        with pytest.raises(SwitchConnectionException):
            ssh_connection._reconnect()

        ssh_connection._connection._open.assert_called_once()
        ssh_connection._connection.enable.assert_called_once()

    def test__check_connection_connection_established(self, ssh_connection, mocker):
        log_debug = mocker.patch("mfd_switchmanagement.connections.ssh.logger.log")
        ssh_connection._connection.is_alive = mocker.Mock(return_value=True)
        return_value = ssh_connection._check_connection()
        expected_value = True
        log_debug.assert_called_once_with(level=log_levels.MODULE_DEBUG, msg="Connection established.")
        assert return_value == expected_value

    def test__check_connection_connection_not_established(self, ssh_connection, mocker):
        log_debug = mocker.patch("mfd_switchmanagement.connections.ssh.logger.log")
        ssh_connection._connection.is_alive = mocker.Mock(return_value=False)
        return_value = ssh_connection._check_connection()
        expected_value = None
        log_debug.assert_called_once_with(level=log_levels.MODULE_DEBUG, msg="Connection not established.")
        assert return_value == expected_value

    def test__remote_reconnect(self, ssh_connection, mocker):
        mocker.patch("mfd_switchmanagement.connections.ssh.logging")
        ssh_connection._check_connection = mocker.Mock(return_value=False)
        ssh_connection._reconnect = mocker.Mock()
        ssh_connection._remote()
        ssh_connection._reconnect.assert_called_once()

    def test__remote_connected(self, ssh_connection, mocker):
        mocker.patch("mfd_switchmanagement.connections.ssh.logging")
        ssh_connection._check_connection = mocker.Mock(return_value=True)
        ssh_connection._reconnect = mocker.Mock()
        ssh_connection._remote()
        ssh_connection._reconnect.assert_not_called()

    def test_connect(self, ssh_connection, mocker):
        expected_params = {
            "host": "10.10.10.10",
            "username": "root",
            "password": "***",
            "secret": "***",
            "key_file": None,
            "use_keys": False,
            "device_type": "SampleSwitch",
            "global_delay_factor": 2,
            "auth_timeout": 60,
        }
        netmiko = mocker.patch("mfd_switchmanagement.connections.ssh.Netmiko")
        ssh_connection._device_type = "SampleSwitch"
        ssh_connection.connect()
        netmiko.assert_called_once_with(**expected_params)

    def test_connect_empty(self, ssh_connection, mocker):
        expected_params = {
            "host": "10.10.10.10",
            "username": "",
            "password": None,
            "secret": "",
            "key_file": None,
            "use_keys": False,
            "device_type": "SampleSwitch",
            "global_delay_factor": 2,
            "auth_timeout": 60,
        }
        ssh_connection._username = None
        ssh_connection._password = ""
        ssh_connection._secret = None
        ssh_connection._device_type = "SampleSwitch"
        netmiko = mocker.patch("mfd_switchmanagement.connections.ssh.Netmiko")
        ssh_connection.connect()
        netmiko.assert_called_once_with(**expected_params)

    def test_connect_auto_detect(self, ssh_connection, mocker):
        expected_params = {
            "host": "10.10.10.10",
            "username": "root",
            "password": "***",
            "secret": "***",
            "key_file": None,
            "use_keys": False,
            "device_type": "SampleSwitch",
            "global_delay_factor": 2,
            "auth_timeout": 60,
        }
        ssh_detect = mocker.patch("mfd_switchmanagement.connections.ssh.SSHDetect")
        netmiko = mocker.patch("mfd_switchmanagement.connections.ssh.Netmiko")
        ssh_detect().autodetect.return_value = "SampleSwitch"
        ssh_connection.connect()
        netmiko.assert_called_once_with(**expected_params)

    def test_exit_port_configuration(self, ssh_connection, mocker):
        ssh_connection._check_connection = mocker.Mock(return_value=True)
        ssh_connection._connection.exit_config_mode = mocker.Mock()
        ssh_connection.exit_port_configuration()
        ssh_connection._connection.exit_config_mode.assert_called_once()
