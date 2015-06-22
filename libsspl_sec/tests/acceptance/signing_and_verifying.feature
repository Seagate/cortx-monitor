Feature: Signing and verifying messages.
    As an sspl user
    I need to be able to sign and verify messages
    To prevent message forgery

    Scenario: Sign and verify a simple message
        Given I set the method to be 'None'
        And my username is "jsmith"
        And my passord is "p4ssw0rd"
        When I generate a session token
        And I sign the following message with my session token:
            """
            "Hello, world!
            """
        Then the message can be verified as authentic.
