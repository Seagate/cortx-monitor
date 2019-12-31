Feature: Test Node Data Sensor Capabilities
	Send node data sensor request messages to SSPL and
	verify the response messages contain the correct information.  Request messages
	are host_update, local_mount_data, cpu_data, if_data, disk_space_alert

Scenario: Send SSPL a node data sensor message requesting interface data
	Given that SSPL is running
	When I send in the node data sensor message to request the current "node:interface:nw" data
	Then I get the if data sensor JSON response message
