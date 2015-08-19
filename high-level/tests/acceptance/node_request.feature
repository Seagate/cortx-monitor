Feature: Node Request
    As a user
    I need a way to query and change the state of cluster nodes
    So that I can administer the cluster

    Scenario Outline: start, stop etc. node
        When I run "python ./cstor/cli/main.py node <command> <nodespec>"
        Then a nodeRequest message to "<command>" "<nodespec>" is sent
        And the exit code is "0"
    Examples:
        | nodespec| command  |
        | node1   | start    |
        | node1   | stop     |
        | node1   | enable   |
        | node1   | disable  |
        | n2      | status   |

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py node invalid_command node1"
        Then the exit code is "2"

    Scenario: Missing nodeName
        When I run "python ./cstor/cli/main.py node start"
        Then the exit code is "2"

    Scenario: list nodes
        When I run "python ./cstor/cli/main.py node list"
        Then the exit code is "0"
