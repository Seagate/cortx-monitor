
Feature: Test Node Data Sensor Capabilities
	Send node data sensor request messages to SSPL-LL and
	verify the response messages contain the correct information.  Request messages
	are host_update, local_mount_data, cpu_data, if_data.

Scenario: Send SSPL-LL a node data sensor message requesting host update data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "host_update" data
	Then I get the "host_update" JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting "local mount data" data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "local_mount_data" data
	Then I get the "local_mount_data" JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting cpu data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "cpu_data" data
	Then I get the "cpu_data" JSON response message

Scenario: Send SSPL-LL a node data sensor message requesting interface data
	Given that SSPL-LL is running
	When I send in the node data sensor message to request the current "if_data" data
	Then I get the "if_data" JSON response message
