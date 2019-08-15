
Feature: Test PSU Sensor Capabilities
	Send PSU sensor request messages to SSPL-LL and
	verify the response messages contain the correct information.

Scenario: Send SSPL-LL a psu sensor message requesting psu data
	Given that SSPL-LL is running
	When I send in the psu sensor message to request the current "enclosure_psu_alert" data
	Then I get the psu sensor JSON response message

