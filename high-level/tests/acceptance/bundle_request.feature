Feature: Support Bundle Request
    As a user
    I need a way to process the support_bundle requests

    Scenario: bundle create
        When I run "python ./cstor/cli/main.py bundle create"
        Then the exit code is "0"

    Scenario: bundle list
        When I run "python ./cstor/cli/main.py bundle list"
        Then the exit code is "0"

    Scenario Outline: create bundle
        When I run "python ./cstor/cli/main.py bundle <command>"
        Then a create bundleRequest message to "<command>" is sent
        And the exit code is "0"
    Examples:
        | command |
        | create  |

    Scenario Outline: list bundle
        When I run "python ./cstor/cli/main.py bundle <command>"
        Then a list bundleRequest message to "<command>" is sent
        And the exit code is "0"
    Examples:
        | command |
        | list    |