Feature: S3admin AccessKey Requests
    As a user
    I need a way to process the s3admin access_key requests

    Scenario: access key operations: create, list with no parameters.
    When I run "python ./cstor/cli/main.py s3admin access_key <command>"
    Then the error output contains "error: argument -u/--user_name is required"
    And the exit code is "2"
    Examples:
        | command   |
        | create    |
        | list      |

    Scenario: access key operations: remove, modify with no parameters.
    When I run "python ./cstor/cli/main.py s3admin access_key <command>"
    Then the error output contains "error: argument -K/--user_access_key is required"
    And the exit code is "2"
    Examples:
        | command   |
        | modify    |
        | remove    |

    Scenario: access key operations: create, list providing only user name.
    When I run "python ./cstor/cli/main.py s3admin access_key <command> -u valid_name"
    Then the output contains "Error: Either Account name or Secret key and Access key are required."
    Examples:
        | command   |
        | create    |
        | list      |

    Scenario: access key operations: remove, modify; providing only user access key.
    When I run "python ./cstor/cli/main.py s3admin access_key <command> -K Any_Valid_Access_Key"
    Then the error output contains "error: argument -u/--user_name is required"
    And the exit code is "2"
    Examples:
        | command   |
        | modify    |
        | remove    |

    #Scenario: access key create,list with Invalid username.
    #When I run "python ./cstor/cli/main.py s3admin access_key <command> -u INVALIDUSER -a admin"
    #Then the output contains "User does not exist. Please enter valid user name.
    #Examples:
    #    | command   |
    #    | create    |
    #    | list      |

    #Scenario: access key create
    #When I run "python ./cstor/cli/main.py s3admin access_key create -u dev -a admin"
    #Then the output contains "User Name"
    #Then the output contains "Access Key"
    #Then the output contains "Secret Key"
    #Then the output contains "Status"
    #And the exit code is "0"

    #Scenario: create duplicate access key
    #When I run "python ./cstor/cli/main.py s3admin access_key create -u dev -a admin"
    #Then the output contains "User Name"
    #Then the output contains "Access Key"
    #Then the output contains "Secret Key"
    #Then the output contains "Status"
    #And the exit code is "0"

    #Scenario: create more than 2 access keys for same user.
    #When I run "python ./cstor/cli/main.py s3admin access_key create -u dev -a admin"
    #Then the output contains "Maximum two Access Keys can be allocated to each User."

    #Scenario: list access keys of specified user
    #When I run "python ./cstor/cli/main.py s3admin access_key list -u dev -a admin"
    #Then the output contains "Status"
    #Then the output contains "Access Key"
    #Then the output contains "User Name"
    #And the exit code is "0"

    Scenario: modify access key without providing account details.
    When I run "python ./cstor/cli/main.py s3admin access_key modify -K any_valid_access_key -u dev -t Inactive"
    Then the output contains "Error: Either Account name or Secret key and Access key are required."

    Scenario: modify access key without providing invalid status.
    When I run "python ./cstor/cli/main.py s3admin access_key modify -K any_valid_access_key -u dev -t InvalidStatus"
    Then the error output contains "error: argument -t/--status: invalid choice"
    Then the error output contains "(choose from 'Active', 'Inactive')"
    And the exit code is "2"

    #Scenario: modify access key with Invalid access key length
    #When I run "python ./cstor/cli/main.py s3admin access_key modify -K fake_access_key -u dev -t Inactive -a admin"
    #Then the output contains "Invalid length for parameter AccessKeyId, value: 15, valid range: 16-32"

    #Scenario: modify access key with Invalid access key.
    #When I run "python ./cstor/cli/main.py s3admin access_key modify -K _fake_access_key_ -u dev -t Inactive -a admin"
    #Then the output contains "Access key/User does not exist. Please enter another valid Access Key/User."

    #Scenario: modify access key
    #When I run "python ./cstor/cli/main.py s3admin access_key modify -K valid_access_key -u dev -t Inactive -a admin"
    #Then the output contains "Access Key updated Successfully !!"
    #And the exit code is "0"

    #Scenario: remove access key which do not exists
    #When I run "python ./cstor/cli/main.py s3admin access_key remove -K _fake_access_key_ -u dev -a admin"
    #Then the output contains "Access key/User does not exist. Please enter another valid Access Key/User."

    #Scenario: remove access key
    #When I run "python ./cstor/cli/main.py s3admin access_key remove -K _valid_access_key -u dev -a admin"
    #Then the output contains "Access Key removed Successfully !!"
    #And the exit code is "0"
