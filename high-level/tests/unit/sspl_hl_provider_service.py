import unittest
import pika
import mock
import json
from sspl_hl.providers.service.provider import Provider


class SsplHlProviderService(unittest.TestCase):
    @staticmethod
    def _generate_expected_message(service_name, command):
        return json.dumps(json.loads("""
            {{
                "serviceRequest":
                {{
                    "serviceName": "{service_name}",
                    "command": "{command}"
                }}
            }}
            """.format(service_name=service_name, command=command)))

    @staticmethod
    def _query_provider(args):
        provider = Provider("service", "description")
        provider.on_create()
        provider.query(
            uri=None,
            columns=None,
            selection_args=args,
            sort_order=None,
            range_from=None,
            range_to=None,
            responder=mock.MagicMock()
            )

    def _test_service_query(self, command):
        expected = self._generate_expected_message(
            service_name="crond", command=command
            )

        with mock.patch('pika.BlockingConnection') as p1:
            self._query_provider(
                args={'command': command, 'serviceName': 'crond'}
                )

        p1().channel().basic_publish.assert_called_with(
            body=expected,
            routing_key='sspl_hl_cmd',
            exchange='sspl_hl_cmd'
            )

    def test_service_queries(self):
        """ Ensures restarting,etc a service generates the proper json message.
        """
        self._test_service_query('restart')
        self._test_service_query('start')
        self._test_service_query('stop')
        self._test_service_query('enable')
        self._test_service_query('disable')
        self._test_service_query('status')

if __name__ == '__main__':
    unittest.main()
