
Feature: Test PSU Sensor Capabilities
	Send PSU sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a psu sensor message requesting psu data
	Given that SSPL is running
	When I send in the psu sensor message to request the current "enclosure:fru:psu" data
	Then I get the psu sensor JSON response message

