# Version 1.0.0
[SSPL-LL_SETTING]
core_processors=PlaneCntrlRMQingressProcessor, PlaneCntrlRMQegressProcessor

message_handlers=PlaneCntrlMsgHandler

sensors=

actuators=


[SYSTEM_INFORMATION]
operating_system=centos6
products=CS-L, CS-G
cli_type=SED

[PLANECNTRLRMQINGRESSPROCESSOR]
virtual_host=SSPL
queue_name=ras_control
exchange_name=ras_sspl
routing_key=sspl_ll
username=sspluser
password=sspl4ever
primary_rabbitmq_server=puppet
secondary_rabbitmq_server=nfsserv

[PLANECNTRLRMQEGRESSPROCESSOR]
virtual_host=SSPL
queue_name=ras_status
exchange_name=ras_sspl
routing_key=sspl_ll
username=sspluser
password=sspl4ever
message_signature_username=sspl-ll
message_signature_token=ALOIUD986798df69a8koDISLKJ282983
message_signature_expires=3600
primary_rabbitmq_server=puppet
secondary_rabbitmq_server=nfsserv


