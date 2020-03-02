#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from google.protobuf import empty_pb2 as empty_proto
from cert.event_stream import EventStream
from captures import ReadBdAddrCompleteCapture
from captures import ConnectionCompleteCapture
from captures import ConnectionRequestCapture
from bluetooth_packets_python3 import hci_packets
from cert.truth import assertThat
from hci.facade import facade_pb2 as hci_facade


class PyHciAclConnection(object):

    def __init__(self, handle, acl_stream, device):
        self.handle = handle
        self.acl_stream = acl_stream
        self.device = device

    def send(self, pb_flag, b_flag, data):
        acl_msg = hci_facade.AclMsg(
            handle=int(self.handle),
            packet_boundary_flag=int(pb_flag),
            broadcast_flag=int(b_flag),
            data=data)
        self.device.hci.SendAclData(acl_msg)

    def send_first(self, data):
        self.send(hci_packets.PacketBoundaryFlag.FIRST_AUTOMATICALLY_FLUSHABLE,
                  hci_packets.BroadcastFlag.POINT_TO_POINT, bytes(data))

    def send_continuing(self, data):
        self.send(hci_packets.PacketBoundaryFlag.CONTINUING_FRAGMENT,
                  hci_packets.BroadcastFlag.POINT_TO_POINT, bytes(data))


class PyHci(object):

    def __init__(self, device):
        self.device = device

        self.device.hci.register_for_events(
            hci_packets.EventCode.ROLE_CHANGE,
            hci_packets.EventCode.CONNECTION_REQUEST,
            hci_packets.EventCode.CONNECTION_COMPLETE,
            hci_packets.EventCode.CONNECTION_PACKET_TYPE_CHANGED)

        self.event_stream = self.device.hci.new_event_stream()
        self.acl_stream = EventStream(
            self.device.hci.FetchAclPackets(empty_proto.Empty()))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.clean_up()
        return traceback is None

    def __del__(self):
        self.clean_up()

    def clean_up(self):
        self.event_stream.shutdown()
        self.acl_stream.shutdown()

    def get_event_stream(self):
        return self.event_stream

    def get_acl_stream(self):
        return self.acl_stream

    def send_command_with_complete(self, command):
        self.device.hci.send_command_with_complete(command)

    def send_command_with_status(self, command):
        self.device.hci.send_command_with_status(command)

    def enable_inquiry_and_page_scan(self):
        self.send_command_with_complete(
            hci_packets.WriteScanEnableBuilder(
                hci_packets.ScanEnable.INQUIRY_AND_PAGE_SCAN))

    def read_own_address(self):
        self.send_command_with_complete(hci_packets.ReadBdAddrBuilder())
        read_bd_addr = ReadBdAddrCompleteCapture()
        assertThat(self.event_stream).emits(read_bd_addr)
        return read_bd_addr.get().GetBdAddr()

    def initiate_connection(self, remote_addr):
        self.send_command_with_status(
            hci_packets.CreateConnectionBuilder(
                remote_addr.decode('utf-8'),
                0xcc18,  # Packet Type
                hci_packets.PageScanRepetitionMode.R1,
                0x0,
                hci_packets.ClockOffsetValid.INVALID,
                hci_packets.CreateConnectionRoleSwitch.ALLOW_ROLE_SWITCH))

    def accept_connection(self):
        connection_request = ConnectionRequestCapture()
        assertThat(self.event_stream).emits(connection_request)

        self.send_command_with_status(
            hci_packets.AcceptConnectionRequestBuilder(
                connection_request.get().GetBdAddr(),
                hci_packets.AcceptConnectionRequestRole.REMAIN_SLAVE))
        return self.complete_connection()

    def complete_connection(self):
        connection_complete = ConnectionCompleteCapture()
        assertThat(self.event_stream).emits(connection_complete)

        handle = connection_complete.get().GetConnectionHandle()
        return PyHciAclConnection(handle, self.acl_stream, self.device)