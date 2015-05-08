
Feature: Test Systemd Watchdog Services Capabilities
	Manipulate various services and verify that the watchdog sensor
	detects the changes and transmits the appropriate json msg

Scenario: Stop the crond service and verify the watchdog transmits correct json msg
	Given that the "crond" service is "running" and SSPL_LL is running
	When I "stop" the "crond" service
	Then I receive a service watchdog json msg with service name "crond.service" and state of "inactive"

Scenario: Start the crond service and verify the watchdog transmits correct json msg
	Given that the "crond" service is "halted" and SSPL_LL is running
	When I "start" the "crond" service
	Then I receive a service watchdog json msg with service name "crond.service" and state of "active"

Scenario: Ungracefully halt the running crond service with SIGKILL and verify the watchdog transmits correct json msg
	Given that the "crond" service is "running" and SSPL_LL is running
	When I ungracefully halt the "crond" service with signal "9"
	Then I receive a service watchdog json msg with service name "crond.service" and state of "failed"

Scenario: Ungracefully halt the running crond service with SIGTERM and verify the watchdog transmits correct json msg
	Given that the "crond" service is "running" and SSPL_LL is running
	When I ungracefully halt the "crond" service with signal "15"
	Then I receive a service watchdog json msg with service name "crond.service" and state of "inactive"

Scenario: Stop the dcs-collector service and verify the watchdog transmits correct json msg
	Given that the "dcs-collector" service is "running" and SSPL_LL is running
	When I "stop" the "dcs-collector" service
	Then I receive a service watchdog json msg with service name "dcs-collector.service" and state of "inactive"

Scenario: Start the dcs-collector service and verify the watchdog transmits correct json msg
	Given that the "dcs-collector" service is "halted" and SSPL_LL is running
	When I "start" the "dcs-collector" service
	Then I receive a service watchdog json msg with service name "dcs-collector.service" and state of "active"