Feature: S3admin User Requests
    As a user
    I need a way to process the s3admin user requests

    Scenario: user create,remove with no parameters.
        When I run "python ./cstor/cli/main.py s3admin user <command>"
        Then the error output contains "error: argument -u/--user_name is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create,remove with only name.
        When I run "python ./cstor/cli/main.py s3admin user <command> -u Test"
        Then the output contains "Error: Either Account name or Secret key and Access key are required."
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create,remove with only account name.
        When I run "python ./cstor/cli/main.py s3admin user <command> -a Seagate"
        Then the error output contains "error: argument -u/--user_name is required" 
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create,remove with only access key.
        When I run "python ./cstor/cli/main.py s3admin user <command> -k TmktL5pdTqy3aSrMKuoKIQ"
        Then the error output contains "error: argument -u/--user_name is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |

    Scenario: user create,remove with only secret key.
        When I run "python ./cstor/cli/main.py s3admin user <command> -s jo5VMdrCkxZiQ7TN5462A1Tl4uENWlmFsw1C+eJA"
        Then the error output contains "error: argument -u/--user_name is required"
        And the exit code is "2"
        Examples:
            | command   |
            | create    |
            | remove    |
 
    # Note: Below scenarios are disabled due to lack of support of IAM and S3 server.
    #
    #Scenario: user create,remove with invalid account name.
    #    When I run "python ./cstor/cli/main.py s3admin user <command> -u Test -a <input>"
    #    Then the output contains "Error: Unable to get Account secret key and access key"
    #    Examples:
    #        | command   |  input   |
    #        | create    | NOTFOUND |
    #        | remove    | NOTFOUND |

    #Scenario: user create, remove  with invalid access_key and secret_key.
    #    When I run "python ./cstor/cli/main.py s3admin user <command> -u Test -s <secret_key> -k <access_key>"
    #    Then the output contains "Either Invalid Access key or Secret key entered."
    #    Examples:
    #        | command   | access_key              | secret_key                               |
    #        | create    | fake_access_key         | fake_secret_key                          |
    #        | create    | CFPIOl5IQ7ShUkmHNnWi_w  | O3T6V0bdVTKATMazLaxK14k0kOEreP2Ha0CQbK/G |
    #        | remove    | fake_access_key         | rAK7wbO8ns7Fd5AFfsnWSma74rauN0v5xmMImA2J |
    #        | remove    | cvPfTQRPQEK_qUmzPBBicg  | fake_secret_key

    #Scenario: user create with account name.
    #    When I run "python ./cstor/cli/main.py s3admin account create -n Seagate -e admin@seagate.com"
    #    When I run "python ./cstor/cli/main.py s3admin user create -u dev -a Seagate"
    #    Then the output contains "User ID" 
    #    Then the output contains "User Name"
    #    Then the output contains "Path"
    #    Then the output contains "ARN"
    #    And the exit code is "0"

    #Scenario: user create with credentials (access key and secret key) 
    #    When I run "python ./cstor/cli/main.py s3admin user create -u test1 -s rAK7wbO8ns7Fd5AFfsnWSma74rauN0v5xmMImA2J -k cvPfTQRPQEK_qUmzPBBicg"
    #    Then the output contains "User ID" 
    #    Then the output contains "User Name"
    #    Then the output contains "Path"
    #    Then the output contains "ARN"
    #    And the exit code is "0"

    #Scenario: user create with existing user name.
    #    When I run "python ./cstor/cli/main.py s3admin user create -u dev -a Seagate"
    #    Then the output contains "User already exist. Please enter another User Name."
    
    #Scenario: user list
    #    When I run "python ./cstor/cli/main.py s3admin user list -a Seagate"
    #    Then the output contains "User Name" 
    #    Then the output contains "User ID"
    #    Then the output contains "ARN"
    #    Then the output contains "Path"
    #    And the exit code is "0"

    Scenario: user list  without specifying account name.
        When I run "python ./cstor/cli/main.py s3admin user list"
        Then the output contains "Either Account name or Secret key and Access key are required.."

    #Scenario: List users of an undefined account
    #    When I run "python ./cstor/cli/main.py s3admin user list -a INVALIDACCOUNT"
    #    Then the output contains "Unable to get Account secret key and access key for 'INVALIDACCOUNT'"

    Scenario: Modify user operation without passing any parameter
        When I run "python ./cstor/cli/main.py s3admin user modify"
        Then the error output contains "error: argument -o/--old_user_name is required"
        And the exit code is "2"

    Scenario: Modify user providing only old user name.
        When I run "python ./cstor/cli/main.py s3admin user modify -o dev"
        Then the error output contains "error: argument -u/--new_user_name is required"
        And the exit code is "2"

    #Scenario: Modify user providing old user name and new user name.
    #    When I run "python ./cstor/cli/main.py s3admin user modify -o dev -u new_dev"
    #    Then the output contains "Either Account name or Secret key and Access key are required.."

    #Scenario: Modify user providing old username that do not exists.
    #    When I run "python ./cstor/cli/main.py s3admin user modify -o seagate -u seagate_dev -a Seagate"
    #    Then the output contains "User does not exist. Please enter another User Name."

    #Scenario: Modify user providing invalid account name.
    #    When I run "python ./cstor/cli/main.py s3admin user modify -o dev -u new_dev -a INVALIDACCOUNT"
    #    Then the output contains "Unable to get Account secret key and access key for 'INVALIDACCOUNT'"

    #Scenario: Modify user
    #    When I run "python ./cstor/cli/main.py s3admin user modify -o dev -u new_dev -a Seagate"
    #    Then the output contains "User modified Successfully !!"
    #    And the exit code is "0"

    #Scenario: Remove invalid user
    #    When I run "python ./cstor/cli/main.py s3admin user remove -u seagate -a Seagate"
    #    Then the output contains "User does not exist. Please enter another User Name."

    #Scenario: Remove user
    #    When I run "python ./cstor/cli/main.py s3admin user remove -u new_dev -a Seagate"
    #    Then the output contains "User removed Successfully !!"
    #    And the exit code is "0"
