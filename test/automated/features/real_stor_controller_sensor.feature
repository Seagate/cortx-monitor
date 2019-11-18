Feature: Test Controller Sensor Capabilities
	Send Controller sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a controller sensor message requesting controller data
	Given that SSPL is running
	When I send in the controller sensor message to request the current "enclosure:fru:controller" data
	Then I get the controller sensor JSON response message

