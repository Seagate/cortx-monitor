Feature: Power Request
    As a user
    I need a way to query and change the state of cluster nodes
    So that I can administer the cluster


    Scenario: power on
        When I run "python ./cstor/cli/main.py power on"
        Then the exit code is "1"

    Scenario: power off
        When I run "python ./cstor/cli/main.py power off"
        Then the exit code is "1"

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py power invalid_command"
        Then the exit code is "2"

    Scenario: Missing command
        When I run "python ./cstor/cli/main.py power "
        Then the exit code is "2"
