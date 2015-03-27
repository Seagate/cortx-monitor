
Feature: Test Systemd Services Capabilities
	Send systemd service actuator messages to SSPL-LL and verify action
	was correctly applied to the service.  Actuator messages for the
	SystemdService class are start | stop | restart | status

Scenario: Send SSPL-LL a systemd service actuator message to restart crond service
	Given that the "crond" service is "running" and SSPL_LL is running
	When I send in the actuator message to "restart" the "crond.service"
	Then SSPL_LL "restart" the "crond.service" and I get the service is "active" response

Scenario: Send SSPL-LL a systemd service actuator message to start crond service
	Given that the "crond" service is "halted" and SSPL_LL is running
	When I send in the actuator message to "start" the "crond.service"
	Then SSPL_LL "start" the "crond.service" and I get the service is "active" response

Scenario: Send SSPL-LL a systemd service actuator message to stop crond service
	Given that the "crond" service is "running" and SSPL_LL is running
	When I send in the actuator message to "stop" the "crond.service"
	Then SSPL_LL "stop" the "crond.service" and I get the service is "inactive" response

Scenario: Send SSPL-LL a systemd service actuator message to get the status of halted crond service
	Given that the "crond" service is "halted" and SSPL_LL is running
	When I send in the actuator message to "status" the "crond.service"
	Then SSPL_LL "status" the "crond.service" and I get the service is "inactive" response

Scenario: Send SSPL-LL a systemd service actuator message to get the status of running crond service
	Given that the "crond" service is "running" and SSPL_LL is running
	When I send in the actuator message to "status" the "crond.service"
	Then SSPL_LL "status" the "crond.service" and I get the service is "active" response