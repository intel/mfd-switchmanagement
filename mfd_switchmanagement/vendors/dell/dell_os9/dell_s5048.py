"""Module for S5048."""

# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from .dell_force10 import DellOS9_Force10
from mfd_switchmanagement.exceptions import SwitchException


class DellOS9_S5048(DellOS9_Force10):
    """Class for Dell S5048."""

    def is_port_linkup(self, port: str) -> bool:
        """
        Check port link up.

        :param port: port of switch
        :return: Status of link
        """
        comm = f"show interfaces {port} status"
        output = self._connection.send_command(comm)
        if "Down" in output:
            return False
        elif "Up" in output:
            return True
        else:
            raise SwitchException(f"Link status parsing error on: {self.__class__.__name__}; interface: {port})")
