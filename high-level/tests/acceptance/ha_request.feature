Feature: Ha Request
    As a user
    I need a way to query the state of Halon

    Scenario Outline: debug show,info status etc. commands to run
        When I run "python ./cstor/cli/main.py ha <command> <subcommand>"
        Then a command request to ha with "<command>" "<subcommand>" is sent
        And the exit code is "0"
    Examples:
        | command | subcommand |
        | debug   | show    |
        | debug   | status  |
        | info    | show    |
        | info    | status  |


    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py ha invalid_command"
        Then the exit code is "2"

    Scenario: Missing serviceName
        When I run "python ./cstor/cli/main.py ha debug show blah"
        Then the exit code is "2"
