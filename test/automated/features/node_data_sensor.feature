# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

Feature: Test Node Data Sensor Capabilities
	Send node data sensor request messages to SSPL and
	verify the response messages contain the correct information.  Request messages
	are host_update, local_mount_data, cpu_data, if_data, disk_space_alert.

Scenario: Send SSPL a node data sensor message requesting host update data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "host_update" data
	Then I get the host update data sensor JSON response message

Scenario: Send SSPL a node data sensor message requesting "local mount data" data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "local_mount_data" data
	Then I get the local mount data sensor JSON response message

Scenario: Send SSPL a node data sensor message requesting cpu data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "cpu_data" data
	Then I get the cpu data sensor JSON response message

Scenario: Send SSPL a node data sensor message requesting interface data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "if_data" data
	Then I get the if data sensor JSON response message

Scenario: Send SSPL a node data sensor message requesting disk space usage data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "disk_space_alert" data
	Then I get the disk space data sensor JSON response message
