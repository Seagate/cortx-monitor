
from  eos.utils.amqp.rabbitmq import RabbitMQAmqpConsumer, RabbitMQAmqpProducer
from framework.base.sspl_constants import MESSAGING, MESSAGING_TYPE_RABBITMQ
from framework.utils.config_reader import ConfigReader

class messagingFactory(object):
    
    def __init__(self):
        """init method"""
        self._conf_reader = ConfigReader()
        self.messaging_bus_type = self._conf_reader._get_value_with_default(section=MESSAGING, 
                                            key="type", default_value=MESSAGING_TYPE_RABBITMQ)

    def get_messaging_producer(self, **configurations):
        if self.messaging_bus_type == MESSAGING_TYPE_RABBITMQ:
            return RabbitMQAmqpProducer(**configurations)
        else:
            raise Exception(f"{self.messaging_bus_type} module is not supported")

    def get_messaging_consumer(self, **configurations):
        if self.messaging_bus_type == MESSAGING_TYPE_RABBITMQ:
            return RabbitMQAmqpConsumer(**configurations)
        else:
            raise Exception(f"{self.messaging_bus_type} module is not supported")

messaging_factory = messagingFactory()
