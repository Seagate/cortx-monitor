""" Base class for sspl_hl.providers tests"""

# Standard libraries
import datetime
import unittest
import json

# Third party imports
import mock

# Local imports
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from plex.core.provider.data_store_provider import ProviderQueryRequest


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


class BaseUnitTest(unittest.TestCase):
    # pylint: disable=too-many-public-methods

    """ Base class containing common methods
    """

    def setUp(self):
        self._patch_ste_submit = mock.patch.object(
            SingleThreadExecutor, 'submit',
            # pylint: disable=star-args, bad-option-value
            side_effect=lambda fn, *args, **kwargs:
            fn(*args, **kwargs)
        )
        self._patch_ste_submit.start()

    def tearDown(self):
        self._patch_ste_submit.stop()

    @staticmethod
    def _query_provider(args,
                        request=mock.MagicMock(spec=ProviderQueryRequest),
                        provider=None):
        """ Calls actual on_create() and query() method of a provider with
            arguments
        :param args: Dictionary of arguments to be supplied as a
               <selection_args> parameter of query() method of
               provider
        :param responder: Mock responder object used to return response
        :param provider: Object of a Provider class tests are executed for
        :return: None
        """
        provider.on_create()
        request.selection_args = args
        provider.render_query(request=request)

    def _test_entity_query(self,
                           selection_args,
                           msg_gen_method,
                           msg_gen_method_args,
                           provider):
        """ Calls self._query_provider() with command
        @param: selection_args:
        @type:
        @param: msg_gen_method:
        @param: msg_gen_method_args

        @return:
        @rtype
        """
        with mock.patch('uuid.uuid4', return_value='uuid_goes_here'), \
                mock.patch('pika.BlockingConnection') as patch:
            # pylint: disable=protected-access,star-args
            expected = json.dumps(msg_gen_method(**msg_gen_method_args))
            # pylint: enable=protected-access
            self._query_provider(args=selection_args, provider=provider)

        patch().channel().basic_publish.assert_called_with(
            body=expected,
            routing_key='sspl_hl_cmd',
            exchange='sspl_hl_cmd'
        )

    def _test_args_validation_cases(self,
                                    command_args,
                                    response_msg,
                                    provider):
        """ Generic method to cases miscellaneous cases
            command_args: Dictionary of arguments to be
                          supplied to command.
                          Ex.{'nodeName': 'node1'} for node
            response_msg: Text to be sent in response
        """
        request_mock = mock.MagicMock(spec=ProviderQueryRequest)
        self._query_provider(
            args=command_args,
            request=request_mock,
            provider=provider
        )
        request_mock.responder.reply_exception.assert_called_once_with(
            response_msg
        )
