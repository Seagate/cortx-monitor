
from  eos.utils.amqp.rabbitmq import RabbitMQAmqpConsumer, RabbitMQAmqpProducer
from framework.utils.config_reader import ConfigReader

class AmqpFactory(object):
    
    def __init__(self):
        """init method"""
        self._conf_reader = ConfigReader()
        self.amqp_type = self._conf_reader._get_value_with_default(section="AMQP", 
                                            key="type", default_value="rabbitmq")

    def get_amqp_producer(self, **configurations):
        if self.amqp_type == 'rabbitmq':
            return RabbitMQAmqpProducer(**configurations)
        else:
            raise Exception(f"{self.amqp_type} module is not supported")

    def get_amqp_consumer(self, **configurations):
        if self.amqp_type == 'rabbitmq':
            return RabbitMQAmqpConsumer(**configurations)
        else:
            raise Exception(f"{self.amqp_type} module is not supported")

amqp_factory = AmqpFactory()
