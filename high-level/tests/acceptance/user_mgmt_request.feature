Feature: User_mgmt Request
    As a user
    I need a way to process the User management requests

    Scenario: user
        When I run "python ./cstor/cli/main.py user"
        Then the exit code is "2"

    Scenario: Invalid command
        When I run "python ./cstor/cli/main.py user invalid_command"
        Then the exit code is "2"

    Scenario: Missing command
        When I run "python ./cstor/cli/main.py "
        Then the exit code is "2"

    Scenario: user create
        When I run "python ./cstor/cli/main.py user create"
        Then the exit code is "2"

    Scenario: user remove
        When I run "python ./cstor/cli/main.py user remove"
        Then the exit code is "2"

    Scenario: user create, remove with no parameters.
        When I run "python ./cstor/cli/main.py user <command>"
        Then the error output contains "error: argument -u/--username is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create with only username.
        When I run "python ./cstor/cli/main.py user <command> -u Test"
        Then the error output contains "error: argument -p/--password is required"
        Examples:
            | command   |
            | create    |

    Scenario: user create, remove with only password.
        When I run "python ./cstor/cli/main.py user <command> -p Seagate123"
        Then the error output contains "error: argument -u/--username is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create, remove with only capabilities.
        When I run "python ./cstor/cli/main.py user <command> -c ras s3"
        Then the error output contains "error: argument -u/--username is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create.
        When I run "python ./cstor/cli/main.py user <command> -u test -p pwd -c ras"
        Then the user_create output contains "successfully created and authorized"
        And the exit code is "0"
        Examples:
            | command   |
            | create    |

    Scenario: user remove.
        When I run "python ./cstor/cli/main.py user <command> -u test"
        Then the user_remove output contains "successfully removed"
        And the exit code is "0"
        Examples:
            | command   |
            | remove    |




