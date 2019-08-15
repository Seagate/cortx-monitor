
Feature: Test Node Data Sensor Capabilities
	Send node data sensor request messages to SSPL-LL and
	verify the response messages contain the correct information.  Request messages
	are host_update, local_mount_data, cpu_data, if_data, disk_space_alert.

Scenario: Send SSPL-LL a node data sensor message requesting host update data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "host_update" data
	Then I get the host update data sensor JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting "local mount data" data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "local_mount_data" data
	Then I get the local mount data sensor JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting cpu data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "cpu_data" data
	Then I get the cpu data sensor JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting interface data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "if_data" data
	Then I get the if data sensor JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting disk space usage data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "disk_space_alert" data
	Then I get the disk space data sensor JSON response message
