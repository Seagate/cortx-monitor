""" Unit tests for sspl_hl.providers.service.provider """


import datetime
import unittest
import mock
import json
from sspl_hl.providers.service.provider import ServiceProvider
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor


class _MyDatetime(datetime.datetime):
    """ Identical to datetime.datetime but reimplements isoformat() to
    record the first call and returns the same value for subsequent
    calls.
    """
    _first_isoformat = None

    def isoformat(self):
        if _MyDatetime._first_isoformat is None:
            _MyDatetime._first_isoformat = \
                super(_MyDatetime, self).isoformat()
        return _MyDatetime._first_isoformat + "FAKE"

# "Monkey-patch" datetime.datetime for these tests to effectively freeze the
# time.  This must be done before we start to import other modules.
datetime.datetime = _MyDatetime


# pylint: disable=too-many-public-methods
class SsplHlProviderService(unittest.TestCase):
    """ Test methods of the
        sspl_hl.providers.service.provider.ServiceProvider object.
    """
    def setUp(self):
        self._patch_ste_submit = mock.patch.object(
            SingleThreadExecutor, 'submit',
            side_effect=lambda fn, *args, **kwargs:
            fn(*args, **kwargs)  # pylint: disable=star-args
            )
        self._patch_ste_submit.start()

    def tearDown(self):
        self._patch_ste_submit.stop()

    @staticmethod
    def _query_provider(args, responder=mock.MagicMock()):
        provider = ServiceProvider("service", "description")
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
        with mock.patch('uuid.uuid4', return_value='uuid_goes_here'), \
                mock.patch('pika.BlockingConnection') as patch:

            # pylint: disable=protected-access
            exp = json.dumps(ServiceProvider._generate_service_request_msg(
                service_name="crond",
                command=command,
                ))
            # pylint: enable=protected-access

            self._query_provider(
                args={'command': command, 'serviceName': 'crond'}
                )
        print exp
        patch().channel().basic_publish.assert_called_with(
            body=exp,
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

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as patch:
            responder = mock.MagicMock()
            self._query_provider(
                args={'command': 'invalid_command', 'serviceName': 'crond'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid command: 'invalid_command'"
                )

        self.assertFalse(patch().channel().basic_publish.called)

    def test_extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as patch:
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

        self.assertFalse(patch().channel().basic_publish.called)

    def test_missing_servicename(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as patch:
            responder = mock.MagicMock()
            self._query_provider(
                args={'command': 'restart'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid request: Missing serviceName"
                )

        self.assertFalse(patch().channel().basic_publish.called)

    def test_missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        with mock.patch('pika.BlockingConnection') as patch:
            responder = mock.MagicMock()
            self._query_provider(
                args={'serviceName': 'crond'},
                responder=responder
                )
            responder.reply_exception.assert_called_once_with(
                "Error: Invalid request: Missing command"
                )

        self.assertFalse(patch().channel().basic_publish.called)


if __name__ == '__main__':
    unittest.main()
