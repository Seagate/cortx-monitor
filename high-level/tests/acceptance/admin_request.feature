Feature: admin Request
    As a user
    I need a way to query ldap for users

    Scenario Outline: user list command to run
        When I run "python ./cstor/cli/main.py admin user list"
        Then a command list request to admin with "user" "list" is sent
        And the exit code is "0"

    Scenario Outline: user show command to run
        When I run "python ./cstor/cli/main.py admin <command> <subcommand> <user>"
        Then a command show request to admin with "<command>" "<subcommand>" "<user>" is sent
        And the exit code is "0"
    Examples:
        | command | subcommand | user           |
        | user    | show       | Howard@Cstor   |

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py user invalid_command"
        Then the exit code is "2"

    Scenario: Missing username
        When I run "python ./cstor/cli/main.py user show"
        Then the exit code is "2"

    Scenario: Non-existant username
        When I run "python ./cstor/cli/main.py user show test"
        Then the exit code is "2"

    Scenario: Extra args
        When I run "python ./cstor/cli/main.py user list test"
        Then the exit code is "2"
