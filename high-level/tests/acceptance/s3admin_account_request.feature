Feature: S3admin Account Requests
    As a user
    I need a way to process the s3admin account requests

    Scenario: s3admin command  with no parameters.
        When I run "python ./cstor/cli/main.py s3admin"
        Then the error output contains "error: too few arguments"
        Then the error output contains "usage: main.py s3admin [-h]"
        And the exit code is "2"

    Scenario: s3admin account command  with no parameters.
        When I run "python ./cstor/cli/main.py s3admin account"
        Then the error output contains "error: too few arguments"
        Then the error output contains "usage: main.py s3admin account [-h] {create,list,remove} ..."
        And the exit code is "2"

    Scenario: account create with no parameters.
        When I run "python ./cstor/cli/main.py s3admin account create"
        Then the error output contains "usage: main.py s3admin account create [-h] -n NAME -e EMAIL"
        And the exit code is "2"

    Scenario: account create with only name.
        When I run "python ./cstor/cli/main.py s3admin account create -n Test"
        Then the error output contains "error: argument -e/--email is required"
        And the exit code is "2"

    Scenario: account create with only email.
        When I run "python ./cstor/cli/main.py s3admin account create -e sample@example.com "
        Then the error output contains "error: argument -n/--name is required" 
        And the exit code is "2"

    Scenario: account create with invalid name.
        When I run "python ./cstor/cli/main.py s3admin account create -e sample@example.com -n <input>"
        Then the output contains "Invalid Name"
        Examples:
            | input                                                                |
            | test_test                                                            |
            | testtesttesttesttesttesttesttesttesttesttesttesttesttesttesttesttest |

    Scenario: account create with invalid email.
        When I run "python ./cstor/cli/main.py s3admin account create -n sample -e <input>"
        Then the output contains "Invalid Email"
        Examples:
            | input                  |
            | test_test_test         |
            | test_example.com       |
            | test@                  |
            | test_test@.com         |

    # Note: Below scenarios are disabled due to lack of support of IAM and S3 server.
    #
    #Scenario: account create
    #    When I run "python ./cstor/cli/main.py s3admin account create -n Seagate -e domain1@seagate.com"
    #    When I run "python ./cstor/cli/main.py s3admin user create -u dev -a Seagate"
    #    Then the output contains "Access Key" 
    #    Then the output contains "Secret Key"
    #    Then the output contains "Account ID"
    #    Then the output contains "Canonical Id"
    #    And the exit code is "0"

    #Scenario: account create with existing account name and email.
    #    When I run "python ./cstor/cli/main.py s3admin account create -n Seagate -e domain@seagate.com"
    #    Then the output contains "Account already exist"

    #Scenario: account create
    #    When I run "python ./cstor/cli/main.py s3admin account create -n Seagate1 -e domain1@seagate.com"
    #    Then the output contains "Access Key" 
    #    Then the output contains "Secret Key"
    #    And the exit code is "0"
    #
    #Scenario: account list
    #    When I run "python ./cstor/cli/main.py s3admin account list"
    #    Then the output contains "Name" 
    #    Then the output contains "Email"
    #    Then the output contains "Account ID"
    #    Then the output contains "Canonical Id"
    #    Then the output contains "Seagate"
    #    And the exit code is "0"

    Scenario: account remove with no parameters
        When I run "python ./cstor/cli/main.py s3admin account remove"
        Then the error output contains "error: argument -n/--name is required"
        And the exit code is "2"

    # Note: Below scenarios are disabled due to lack of support of IAM and S3 server.
    #
    #Scenario: account remove with invalid parameters
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n fake"
    #    Then the output contains "Error: Unable to get Account secret key and access key for 'fake'."


    #Scenario: Remove account with fake access key and secret key
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n fake -k fake -s fake"
    #    Then the output contains "Unauthorized Access. Please enter valid Access key and Secret Key."

    #Scenario: Remove account with invalid name with valid access key and secret key
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n fake -k FaK8_tc7RVmydmTAkCwQ4Q -s yY2SKpbjRyRPSa9DI3M8QSF32evTA+LCft8bcXn4"
    #    Then the output contains "Account does not exist."

    #Scenario: Remove account with existing users/accesskeys associated with specified account (Without --force)
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n Seagate"
    #    Then the output contains "Account can not be removed as It have associated Users and Access Keys."
    #    Then the output contains "Please use --force option to remove Account."

    #Scenario: Remove account with existing users/accesskeys associated with specified account (with --force)
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n Seagate --force"
    #    Then the output contains "Account Removed successfully !"
    #    And the exit code is "0"

    #Scenario: Remove account
    #    When I run "python ./cstor/cli/main.py s3admin account remove -n Seagate1"
    #    Then the output contains "Account Removed successfully !"
    #    And the exit code is "0"



