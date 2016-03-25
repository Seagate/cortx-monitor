Feature: Status Request
    As a user
    I need a way to see and change the status of File-stat, power and RAS-SEM,
    So that I can administer it.


    Scenario: status
        When I run "python ./cstor/cli/main.py status"
        Then the exit code is "0"

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py status invalid_command"
        Then the exit code is "2"

    Scenario: Missing command
        When I run "python ./cstor/cli/main.py "
        Then the exit code is "2"
