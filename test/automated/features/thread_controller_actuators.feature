
Feature: Test Thread Controller Capabilities
    Send thread_controller actuator messages to SSPL-LL and
    verify action was correct.  Actuator messages for the
    ThreadController class are start | stop | restart | status.

Scenario: Send SSPL-LL a thread_controller actuator message to restart hpi monitor msg handler
    Given I send in the actuator message to restart hpi monitor
    When SSPL-LL restarts the thread for hpi monitor msg handler
    Then I get the Restart Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator message to stop hpi monitor msg handler
    Given I send in the actuator message to stop hpi monitor
    When SSPL-LL Stops the thread for hpi monitor msg handler
    Then I get the Stop Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator message to start hpi monitor msg handler
    Given I send in the actuator message to start hpi monitor
    When SSPL-LL Starts the thread for hpi monitor msg handler
    Then I get the Start Successful JSON response message

Scenario: Send SSPL-LL a thread_controller actuator to stop hpi monitor and then request thread status
    Given I request to stop hpi monitor and then I request a thread status
    When SSPL-LL Stops the hpi monitor and receives a request for thread status
    Then I get the Stop Successful JSON message then I get the thread status message

Scenario: Send SSPL-LL a thread_controller actuator to start hpi monitor and then request thread status
    Given I request to start hpi monitor and then I request a thread status
    When SSPL-LL Starts the hpi monitor and receives a request for thread status
    Then I get the Start Successful JSON message then I get the thread status message
