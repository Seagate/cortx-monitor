POC code used to connect SSPL service with multiple RabbitMQ nodes in a cluster.
================================================================================
- csm_service_mock.py mocks CSM service.
- sspl_ingress_service_mock.py mocks SSPL ingress service.
- Run sspl_ingress_service_mock.py in two different hosts.
- Run csm_service_mock.py from any host.
- Stop/Start RabbitMQ instances. At a time at-least one rabbitmq instance should be alive.
- There should not be any message loss.
- Refer https://jts.seagate.com/browse/EOS-5749 for more detail.
