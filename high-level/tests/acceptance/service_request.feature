Feature: Service Request
    As a user
    I need a way to query and change the state of cluster services
    So that I can administer the cluster

    Scenario Outline: Restart,etc. service on all nodes
        When I run "./cstor service <command> <service>"
        Then a serviceRequest message to "<command>" "<service>" is sent
    Examples:
        | service | command |
        | crond   | restart |
        | crond   | start   |
        | crond   | stop    |
        | crond   | enable  |
        | crond   | disable |
        | crond   | status  |
