Feature: Test Enclosure Actuator Capabilities
    Send Enclosure request message to SSPL and
    verify the response messages contain the correct information.

Scenario: Send SSPL an enclosure actuator message requesting fan_module data
    Given that SSPL is running
    When I send in the enclosure actuator message to request the current "ENCL:enclosure:fru:fan" data
    Then I get the fan module JSON response message

