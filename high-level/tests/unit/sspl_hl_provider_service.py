import unittest
import pika
import mock
import json
from sspl_hl.providers.service.provider import Provider
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor


class SsplHlProviderService(unittest.TestCase):
    def setUp(self):
        self._p = mock.patch.object(
            SingleThreadExecutor, 'submit',
            side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)
            )
        self._p.start()

    def tearDown(self):
        self._p.stop()

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
    def _query_provider(args, responder=mock.MagicMock()):
        provider = Provider("service", "description")
        provider.on_create()
        provider.query(
            uri=None,
            columns=None,
            selection_args=args,
            sort_order=None,
            range_from=None,
            range_to=None,
            responder=responder
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

    def test_malformed_service_query__bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as p1:
            responder = mock.MagicMock()
            self._query_provider(
                args={'command': 'invalid_command', 'serviceName': 'crond'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid command: 'invalid_command'"
                )

    def test_malformed_service_query__extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as p1:
            responder = mock.MagicMock()
            self._query_provider(
                args={
                    'command': 'restart',
                    'serviceName': 'crond',
                    'extrastuff': 'blah'
                    },
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid request: Extra parameter 'extrastuff' detected"
                )

    def test_malformed_service_query__missing_servicename(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as p1:
            responder = mock.MagicMock()
            self._query_provider(
                args={'command': 'restart'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid request: Missing serviceName"
                )

    def test_malformed_service_query__missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as p1:
            responder = mock.MagicMock()
            self._query_provider(
                args={'serviceName': 'crond'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid request: Missing command"
                )


if __name__ == '__main__':
    unittest.main()
