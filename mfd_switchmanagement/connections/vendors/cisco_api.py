# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Cisco API connection."""

import json
import logging
from typing import List

import requests

from ...connections.api import APISwitchConnection
from ...exceptions import SwitchConnectionException
from mfd_common_libs import add_logging_level, log_levels

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)
add_logging_level("CMD", log_levels.CMD)
add_logging_level("OUT", log_levels.OUT)


class CiscoAPIConnection(APISwitchConnection):
    """Implementation of Cisco API."""

    def __init__(self, *args, **kwargs) -> None:
        """
        Init for Cisco API Connection.

        Set variables
        """
        super().__init__(*args, **kwargs)
        self._http_header = {"content-type": "application/json-rpc"}
        self._url = f"http://{self._ip}/ins"
        self._verify = kwargs.get("verify", False)
        self._ssl_cert = kwargs.get("ssl_cert", None)
        self._ssl_key = kwargs.get("ssl_key", None)
        try:
            self.send_command("show version")
        except Exception as e:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Problem with sending test command to switch")
            raise SwitchConnectionException("Problem with sending test command to switch") from e

    @staticmethod
    def _generate_payload(command_list: List[str]) -> str:
        """
        Generate JSON string from Cisco_NX OS command input.

        :param command_list: comma separated Cisco_NX OS commands to be executed in order on switch
        :return: serialized object as JSON formatted string
        """
        req_list = []

        for nbr, command in enumerate(command_list, start=1):
            req_list.append(
                {
                    "jsonrpc": "2.0",
                    "method": "cli",
                    "params": {"cmd": command, "version": 1},
                    "id": nbr,
                }
            )
        return json.dumps(req_list)

    def send_command(self, command: str) -> list:
        """
        Send command via connection.

        :param command: command for send
        :return: Output from command
        """
        return self.send_command_list([command])

    def send_command_list(self, command_list: List[str]) -> list:
        """
        Send commands to targeted client switch, collect responses, log errors and commands results.

        :param command_list: Cisco_NX OS commands to be executed in order on switch
        :raises SwitchConnectionException: If response is incorrect
        :return: JSON encoded responses
        """
        logger.log(level=log_levels.CMD, msg=f">{self._ip}> {command_list}")

        http_payload = self._generate_payload(command_list)
        try:
            resp = requests.post(
                self._url,
                data=http_payload,
                headers=self._http_header,
                auth=(self._username, self._password),
                verify=self._verify,
                cert=(self._ssl_cert, self._ssl_key) if self._ssl_cert and self._ssl_key else None,
            )
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as request_exception:
            raise SwitchConnectionException("Found problem with switch communication") from request_exception

        if resp.status_code != 200:
            raise SwitchConnectionException(f"Switch responded {resp.status_code} status code")
        raw_json_response = resp.json()
        json_resp = raw_json_response if isinstance(raw_json_response, list) else [raw_json_response]
        for element in json_resp:
            if element.get("error", 0):
                raise SwitchConnectionException(
                    f"{element['error']['message']}{element['error']['data']['msg'].strip()}: "
                    f"{command_list[element['id'] - 1]}"
                )
            elif element.get("result", None) is not None:
                logger.log(level=log_levels.OUT, msg=json.dumps(element["result"].get("body", ""), indent=4))
                logger.log(level=log_levels.OUT, msg=json.dumps(element["result"].get("msg", "")))
        return json_resp
