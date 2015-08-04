""" Unit tests for sspl_hl.providers.service.provider """


import unittest

from sspl_hl.providers.service.provider import ServiceProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods
class SsplHlProviderService(BaseUnitTest):

    """ Test methods of the
        sspl_hl.providers.service.provider.ServiceProvider object.
    """
    SERVICE_COMMAND = ['start',
                       'stop',
                       'restart',
                       'enable',
                       'disable']

    def test_service_queries(self):
        """ Ensures restarting,etc a service generates the proper json message.
        """
        for command in SsplHlProviderService.SERVICE_COMMAND:
            method_args = {'command': command,
                           'service_name': 'crond.service'}
            # pylint: disable=protected-access
            selection_args = {'serviceName': 'crond.service',
                              'command': command}
            self._test_entity_query(
                selection_args,
                ServiceProvider._generate_service_request_msg,
                method_args,
                ServiceProvider('service', ''))

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.
        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'invalid_command',
                        'serviceName': 'crond'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         ServiceProvider('service', ''))

    def test_extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'restart',
                        'serviceName': 'crond',
                        'extrastuff': 'blah'}
        main_msg = "Error: Invalid request:"
        response_msg = " Extra parameter 'extrastuff' detected"
        self._test_args_validation_cases(command_args,
                                         main_msg + response_msg,
                                         ServiceProvider('service', ''))

    def test_missing_servicename(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'restart'}
        response_msg = "Error: Invalid request: Missing serviceName"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         ServiceProvider('service', ''))

    def test_missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'serviceName': 'crond.service'}
        response_msg = "Error: Invalid request: Missing command"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         ServiceProvider('service', ''))


if __name__ == '__main__':
    unittest.main()
