
Feature: Test Disk Sensor Capabilities
	Send Disk sensor request messages to SSPL and
	verify the response messages contain the correct information.

Scenario: Send SSPL a disk sensor message requesting disk data
	Given that SSPL is running
    When I send in the disk sensor message to request the current "enclosure:fru:disk" data
	Then I get the disk sensor JSON response message
