Feature: FRU Request
    As a user
    I need a way to query the list and status values of fru
    So that I can administer the cluster

    Scenario Outline: list, status etc. fru
        When I run "python ./cstor/cli/main.py fru <command> <hwtype>"
        Then a fruRequest message to "<command>" "<hwtype>" is sent
        And the exit code is "0"
    Examples:
        | hwtype| command |
        | node1   | status  |
        | node1   | list    |
        | disk1   | status  |
        | disk1   | list    |

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py fru invalid_command node1"
        Then the exit code is "2"

    Scenario: Missing hwtype
        When I run "python ./cstor/cli/main.py fru status"
        Then the exit code is "2"
