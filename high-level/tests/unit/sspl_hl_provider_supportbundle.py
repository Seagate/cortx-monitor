""" Unit tests for sspl_hl.providers.support_bundle.provider """


import unittest

from sspl_hl.providers.bundle.provider import SupportBundleProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods
class SsplHlProviderSupportBundle(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.support_bundle.provider.SupportBundleProvider object.
    """
    COMMAND = ['create', 'list']

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.
        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """

        command_args = {'command': 'invalid_command'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         SupportBundleProvider(
                                             'support_bundle', ''))

    def test_extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """

        command_args = {'command': 'list',
                        'extrastuff': 'blah'}
        main_msg = "Error: Invalid request:"
        response_msg = " Extra parameter 'extrastuff' detected"

        self._test_args_validation_cases(command_args,
                                         main_msg + response_msg,
                                         SupportBundleProvider(
                                             'support_bundle', ''))

    # def test_missing_command(self):
    #     """
    #     Ensure sending query without command results in an http error code.
    #
    #     The cli should prevent this from happening, so this is just to cover
    #     the case of the user bypassing the cli and accessing the data
    #     provider directly.
    #     """
    #
    #     command_args = {}
    #     response_msg = "Error: Invalid request: Missing command"
    #     self._test_args_validation_cases(command_args,
    #                                      response_msg,
    #                                      SupportBundleProvider(
    #                                          'support_bundle', ''))


if __name__ == '__main__':
    unittest.main()
