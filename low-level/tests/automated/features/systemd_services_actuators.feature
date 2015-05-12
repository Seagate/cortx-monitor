
Feature: Test Systemd Services Capabilities
	Send systemd service actuator messages to SSPL-LL and verify action
	was correctly applied to the service.  Actuator messages for the
	SystemdService class are start | stop | restart | status

Scenario: Send SSPL-LL a systemd service actuator message to restart httpd service
	Given that the "httpd" service is "running" and SSPL_LL is running
	When I send in the actuator message to "restart" the "httpd.service"
	Then SSPL_LL "restart" the "httpd.service" and I get the service is "active" response

Scenario: Send SSPL-LL a systemd service actuator message to start httpd service
	Given that the "httpd" service is "halted" and SSPL_LL is running
	When I send in the actuator message to "start" the "httpd.service"
	Then SSPL_LL "start" the "httpd.service" and I get the service is "active" response

Scenario: Send SSPL-LL a systemd service actuator message to stop httpd service
	Given that the "httpd" service is "running" and SSPL_LL is running
	When I send in the actuator message to "stop" the "httpd.service"
	Then SSPL_LL "stop" the "httpd.service" and I get the service is "inactive" response

Scenario: Send SSPL-LL a systemd service actuator message to get the status of halted httpd service
	Given that the "httpd" service is "halted" and SSPL_LL is running
	When I send in the actuator message to "status" the "httpd.service"
	Then SSPL_LL "status" the "httpd.service" and I get the service is "inactive" response

Scenario: Send SSPL-LL a systemd service actuator message to get the status of running httpd service
	Given that the "httpd" service is "running" and SSPL_LL is running
	When I send in the actuator message to "status" the "httpd.service"
	Then SSPL_LL "status" the "httpd.service" and I get the service is "active" response