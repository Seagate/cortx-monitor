Feature: Service Request
    As a user
    I need a way to query and change the state of cluster services
    So that I can administer the cluster

    Scenario: Restart service on all nodes
        When I request "crond" service "restart" for all nodes
        Then the following message is generated and placed in the queue:
            """
            "{
            "    "serviceRequest":
            "    {
            "        "serviceName": "crond",
            "        "command": "restart""
            "    }
            "}
            """
