Feature: Test Thread Controller Capabilities
    Send thread_controller actuator messages to SSPL-LL and
    verify action was correct.  Actuator messages for the
    ThreadController class are start | stop | restart | status.

Scenario: Send SSPL-LL a thread_controller actuator message to stop raid sensor msg handler
    Given I send in the actuator message to stop raid sensor
    When SSPL-LL Stops the thread for raid sensor msg handler
    Then I get the Stop Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator message to start raid sensor msg handler
    Given I send in the actuator message to start raid sensor
    When SSPL-LL Starts the thread for raid sensor msg handler
    Then I get the Start Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator to stop raid sensor and then request thread status
    Given I request to stop raid sensor and then I request a thread status
    When SSPL-LL Stops the raid sensor and receives a request for thread status
    Then I get the Stop Successful JSON message then I get the thread status message

Scenario: Send SSPL-LL a thread_controller actuator to start raid sensor and then request thread status
    Given I request to start raid sensor and then I request a thread status
    When SSPL-LL Starts the raid sensor and receives a request for thread status
    Then I get the Start Successful JSON message then I get the thread status message
