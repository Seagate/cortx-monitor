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

Feature: Test Enclosure Actuator Capabilities
    Send Enclosure request message to SSPL and
    verify the response messages contain the correct information.

Scenario: Send SSPL an enclosure actuator message requesting fan_module data
    Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:fan" data with instance id "4"
    Then I get the fan module JSON response message

Scenario: Send SSPL an enclosure actuator message requesting fan_module data
    Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:fan" data with instance id "*"
    Then I get the fan module JSON response message

Scenario: Send SSPL-LL a disk actuator message requesting single-instance disk data
	Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:disk" data with instance id "65"
	Then I get the disk actuator JSON response message for disk instance "65"

Scenario: Send SSPL-LL a disk actuator message requesting multi-instance disk data
	Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:disk" data with instance id "*"
	Then I get the disk actuator JSON response message for disk instance "*"

Scenario: Send SSPL an enclosure actuator message requesting controller data
    Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:controller" data with instance id "1"
    Then I get the controller JSON response message

Scenario: Send SSPL an enclosure actuator message requesting temperature sensor data for all sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:temperature" data for "*" sensor
	Then I get the sensor JSON response message for "*" "Temperature" sensor

Scenario: Send SSPL an enclosure actuator message requesting temperature sensor data for specific sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:temperature" data for "CPU Temperature-Ctlr B" sensor
	Then I get the sensor JSON response message for "CPU Temperature-Ctlr B" "Temperature" sensor

Scenario: Send SSPL an enclosure actuator message requesting voltage sensor data for all sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:voltage" data for "*" sensor
	Then I get the sensor JSON response message for "*" "Voltage" sensor

Scenario: Send SSPL an enclosure actuator message requesting voltage sensor data for specific sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:voltage" data for "Capacitor Pack Voltage-Ctlr B" sensor
	Then I get the sensor JSON response message for "Capacitor Pack Voltage-Ctlr B" "Voltage" sensor

Scenario: Send SSPL an enclosure actuator message requesting current sensor data for all sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:current" data for "*" sensor
	Then I get the sensor JSON response message for "*" "Current" sensor

Scenario: Send SSPL an enclosure actuator message requesting current sensor data for specific sensor
	Given that SSPL is running
	When I send in the enclosure actuator request to get the current "ENCL:enclosure:sensor:current" data for "Current 12V Rail Loc: right-PSU" sensor
	Then I get the sensor JSON response message for "Current 12V Rail Loc: right-PSU" "Current" sensor

Scenario: Send SSPL a psu actuator message requesting psu data
	Given that SSPL is running
	When I send in the psu sensor message to request the psu "ENCL:enclosure:fru:psu" data
	Then I get the psu actuator JSON response message for psu instance "*"
	
Scenario: Send SSPL an Enclosure SAS Port message requesting sas port status data
	Given that SSPL is running
	When I send Enclosure SAS Port message to request the current "enclosure:interface:sas" data
	Then I get the Enclosure SAS ports JSON response message
