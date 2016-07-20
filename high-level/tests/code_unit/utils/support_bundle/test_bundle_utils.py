import os
import subprocess
import tarfile
import unittest
import sspl_hl.utils.support_bundle.bundle_utils as utils


class TestBundleUtils(unittest.TestCase):
    """
    Test cases for bundle utils module
    """

    def setUp(self):
        """
        """
        TestBundleUtils._create_fake_bundle_files()

    @staticmethod
    def _create_fake_bundle_files():
        """
        """
        def get_fake_bundles_path():
            """
            Get fake mco absolute path
            """
            bundle_files = "misc_files/bundle_files/"
            current_file_path = os.path.dirname(
                os.path.abspath(os.path.realpath(__file__)))
            bundles_file_path = os.path.join(current_file_path, "../..",
                                             bundle_files)
            return bundles_file_path

        def create_bundle_files():
            """Tar some default files and put it to the
            /var/lib/support_bundles/"""
            tar_file = tarfile.open('2016-07-19_15-20-27.tar', "w:gz")
            tar_file.add(get_fake_bundles_path())
            tar_file.close()

        # Give necessary permissions to it
        subprocess.check_output('sudo chown plex /var/lib/support_bundles',
                                shell=True)
        # create bundle files.
        # command = 'sudo cp {} /var/lib/support_bundles/'.format(
        #     get_fake_bundles_path()
        # )
        # subprocess.check_output(command, shell=True)

        create_bundle_files()

    def tearDown(self):
        TestBundleUtils._clean_fake_bundle_files()

    @staticmethod
    def _clean_fake_bundle_files():
        """
        """
        if os.path.exists('/var/lib/support_bundles/'):
            subprocess.check_output(
                'sudo rm -f /var/lib/support_bundles/*',
                shell=True
            )

    def test_get_bundle_info(self):
        files_info = utils.bundle_files()
        self.assertTrue('completed' in files_info)
        self.assertTrue('in_process' in files_info)
