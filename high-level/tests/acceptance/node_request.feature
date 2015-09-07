Feature: Node Request
    As a user
    I need a way to query and change the state of cluster nodes
    So that I can administer the cluster

    Scenario Outline: start, stop etc. node
        When I run "python ./cstor/cli/main.py node <command> --node_spec <nodespec>"
        Then a nodeRequest message to "<command>" --node_spec "<nodespec>" is sent
        And the exit code is "0"
    Examples:
        | command | nodespec |
        | start   | node1    |
        | stop    | node1    |
        | enable  | node1    |
        | disable | node1    |
        | status  | n2       |

    Scenario Outline: start, stop etc. all node
        When I run "python ./cstor/cli/main.py node <command>"
        Then a nodeRequest message to "<command>" is sent
        And the exit code is "0"
    Examples:
        | command  |
        | status   |
        | stop     |
        | enable   |
        | disable  |
        | start    |

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py node invalid_command node1"
        Then the exit code is "2"

    Scenario: list nodes
        When I run "python ./cstor/cli/main.py node list"
        Then the exit code is "0"
