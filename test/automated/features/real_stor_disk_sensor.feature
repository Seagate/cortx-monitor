
Feature: Test Disk Sensor Capabilities
	Send Disk sensor request messages to SSPL-LL and
	verify the response messages contain the correct information.

Scenario: Send SSPL-LL a disk sensor message requesting disk data
	Given that SSPL-LL is running
	When I send in the disk sensor message to request the current "enclosure_disk_alert" data
	Then I get the "enclosure_disk_alert" JSON response message

