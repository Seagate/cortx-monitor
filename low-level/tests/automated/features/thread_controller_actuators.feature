
Feature: Test Thread Controller Capabilities
	Send thread_controller actuator messages to SSPL-LL and 
	verify action was correct.  Actuator messages for the 
	ThreadController class are start | stop | restart | status.

Scenario: Send SSPL-LL a thread_controller actuator message to restart drive manager msg handler
	Given I send in the actuator message to restart drive manager
	When SSPL-LL restarts the thread for drive manager msg handler
	Then I get the Restart Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator message to stop drive manager msg handler
	Given I send in the actuator message to stop drive manager
	When SSPL-LL Stops the thread for drive manager msg handler
	Then I get the Stop Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator message to start drive manager msg handler
	Given I send in the actuator message to start drive manager
	When SSPL-LL Starts the thread for drive manager msg handler
	Then I get the Start Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator to stop drive manager and then request thread status
	Given I request to stop drive manager and then I request a thread status
	When SSPL-LL Stops the drive manager and receives a request for thread status
	Then I get the Stop Successful JSON message then I get the thread status message

Scenario: Send SSPL-LL a thread_controller actuator to start drive manager and then request thread status
	Given I request to start drive manager and then I request a thread status
	When SSPL-LL Starts the drive manager and receives a request for thread status
	Then I get the Start Successful JSON message then I get the thread status message

Scenario: Send SSPL-LL a thread_controller actuator to stop drive manager and then request thread status
	Given I request to stop drive manager and then I request a thread status
	When SSPL-LL Stops the drive manager and receives a request for thread status
	Then I get the Stop Successful JSON message then I get the thread status message
	
	