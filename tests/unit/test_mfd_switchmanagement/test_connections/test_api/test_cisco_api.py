# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import json
from textwrap import dedent

import pytest
from requests import HTTPError

from mfd_switchmanagement import CiscoAPIConnection
from mfd_switchmanagement.exceptions import SwitchConnectionException


class TestCiscoAPI:
    @pytest.fixture()
    def connection(self, mocker):
        mock_send_command = mocker.Mock(return_value="version")
        mocker.patch.object(CiscoAPIConnection, "send_command", new=mock_send_command)
        params = {"ip": "10.10.10.10", "username": "admin", "password": "***"}
        return CiscoAPIConnection(**params)

    def test_validation_failure(self, mocker):
        mock_send_command = mocker.Mock(side_effect=SwitchConnectionException())
        mocker.patch.object(CiscoAPIConnection, "send_command", new=mock_send_command)
        params = {"ip": "10.10.10.10", "username": "admin", "password": "***"}
        with pytest.raises(SwitchConnectionException):
            CiscoAPIConnection(**params)

    def test_validation(self, mocker):
        mock_send_command = mocker.Mock(return_value="version")
        mocker.patch.object(CiscoAPIConnection, "send_command", new=mock_send_command)
        params = {"ip": "10.10.10.10", "username": "admin", "password": "***"}
        assert CiscoAPIConnection(**params) is not None

    def test__generate_payload(self, connection):
        expected_payload = json.dumps(
            [{"jsonrpc": "2.0", "method": "cli", "params": {"cmd": "show version", "version": 1}, "id": 1}]
        )
        generated = connection._generate_payload(["show version"])
        assert generated == dedent(expected_payload)

    def test_send_command_list(self, connection, mocker):
        json_output = {
            "jsonrpc": "2.0",
            "result": {
                "body": {
                    "header_str": "Cisco Nexus Operating System (NX-OS) Software\n",
                    "bios_ver_str": "08.35",
                    "kickstart_ver_str": "7.0(3)I7(6)",
                    "bios_cmpl_time": "08/31/2018",
                    "kick_file_name": "bootflash:///nxos.7.0.3.I7.6.bin",
                    "kick_cmpl_time": " 3/5/2019 13:00:00",
                    "kick_tmstmp": "03/05/2019 22:04:55",
                    "chassis_id": "Nexus3000 C3232C Chassis",
                    "cpu_name": "Intel(R) Xeon(R) CPU E5-2403 v2 @ 1.80GHz",
                    "memory": 8155648,
                    "mem_type": "kB",
                    "proc_board_id": "FOC212AAAAA",
                    "host_name": "nexus-3232c",
                    "bootflash_size": 53298520,
                    "kern_uptm_days": 9,
                    "kern_uptm_hrs": 17,
                    "kern_uptm_mins": 55,
                    "kern_uptm_secs": 9,
                    "rr_usecs": 907768,
                    "rr_ctime": "Fri Sep 11 17:48:43 2020",
                    "rr_reason": "Reset Requested by CLI command reload",
                    "rr_sys_ver": "7.0(3)I7(6)",
                    "rr_service": "",
                    "manufacturer": "Cisco Systems, Inc.",
                    "TABLE_package_list": {"ROW_package_list": {"package_id": {}}},
                }
            },
            "id": 1,
        }
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json = mocker.Mock(return_value=json_output)
        mock_post = mocker.Mock(return_value=mock_response)
        mocker.patch("requests.post", new=mock_post)
        output = connection.send_command_list(["show version"])
        assert output == [json_output]

    def test_send_command_list_status_code_failure(self, connection, mocker):
        mock_response = mocker.Mock()
        mock_response.status_code = 400
        mock_post = mocker.Mock(return_value=mock_response)
        mocker.patch("requests.post", new=mock_post)
        with pytest.raises(SwitchConnectionException):
            connection.send_command_list(["show version"])

    def test_send_command_list_request_failure(self, connection, mocker):
        mock_post = mocker.Mock(side_effect=HTTPError)
        mocker.patch("requests.post", new=mock_post)
        with pytest.raises(SwitchConnectionException):
            connection.send_command_list(["show version"])
