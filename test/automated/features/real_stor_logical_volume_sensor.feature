Feature: Test Logical Volume Sensor Capabilities
	Send Logical Volume sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a logical volume sensor message requesting logical volume data
	Given that SSPL is running
	When I send in the logical volume sensor message to request the current "enclosure:fru:logical_volume" data
	Then I get the logical volume sensor JSON response message

