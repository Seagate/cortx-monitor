import unittest
import pika
import mock
import json
from sspl_hl.providers.service.provider import Provider


class SsplHlProviderService(unittest.TestCase):
    def test_service_restart_query(self):
        """ Ensures restarting a service generates the proper json message. """
        expected = json.dumps(json.loads("""
            {
                "serviceRequest":
                {
                    "serviceName": "crond",
                    "command": "restart"
                }
            }
            """))

        with mock.patch('pika.BlockingConnection') as p1:
            provider = Provider("service", "description")
            provider.on_create()
            provider.query(
                uri=None,
                columns=None,
                selection_args={'command': 'restart', 'serviceName': 'crond'},
                sort_order=None,
                range_from=None,
                range_to=None,
                responder=mock.MagicMock()
                )

        p1().channel().basic_publish.assert_called_with(
            body=expected,
            routing_key='sspl_hl_cmd',
            exchange='sspl_hl_cmd'
            )


if __name__ == '__main__':
    unittest.main()
