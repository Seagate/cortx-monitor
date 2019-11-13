
Feature: Test Fan module Sensor Capabilities
	Send fan module sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a fan sensor message requesting fan data
	Given that SSPL is running
	When I send in the fan module sensor message to request the current "enclosure:fru:fan" data
	Then I get the fan module sensor JSON response message

