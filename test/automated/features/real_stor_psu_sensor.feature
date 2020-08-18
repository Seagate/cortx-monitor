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

Feature: Test PSU Sensor Capabilities
	Send PSU sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a psu sensor message requesting psu data
	Given that SSPL is running
	When I send in the psu sensor message to request the current "enclosure:fru:psu" data
	Then I get the psu sensor JSON response message

