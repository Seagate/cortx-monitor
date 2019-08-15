
Feature: Test Fan module Sensor Capabilities
	Send fan module sensor request messages to SSPL-LL and
	verify the response messages contain the correct information.

Scenario: Send SSPL-LL a fan sensor message requesting fan data
	Given that SSPL-LL is running
	When I send in the fan module sensor message to request the current "enclosure_fan_module_alert" data
	Then I get the fan module sensor JSON response message

