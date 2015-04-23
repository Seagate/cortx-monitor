Feature: Service Request
    As a user
    I need a way to query and change the state of cluster services
    So that I can administer the cluster

    Scenario Outline: Restart,etc. service on all nodes
        When I run "python ./cli/cstor.py service <command> <service>"
        Then a serviceRequest message to "<command>" "<service>" is sent
        And the exit code is "0"
    Examples:
        | service | command |
        | crond   | restart |
        | crond   | start   |
        | crond   | stop    |
        | crond   | enable  |
        | crond   | disable |
        | crond   | status  |

    Scenario: Invalid command
        When I run "python ./cli/cstor.py service invalid_command crond"
        Then the exit code is "2"

    Scenario: Missing serviceName
        When I run "python ./cli/cstor.py service restart"
        Then the exit code is "2"
