/*
 *
 * Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Affero General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License along
 * with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
 * about this software or licensing, please email opensource@seagate.com or
 * cortx-questions@seagate.com.
 *
 */


#include <check.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>
#include <assert.h>



#include "sspl_sec.h"
#include "sec_method.h"

void _ensure_one_file_present_in_dir(const char* dirname)
{
    /* ensure dir exists */
    struct stat ignored;
    ck_assert_int_eq(stat(dirname, &ignored), 0);

    /* count files in dir */
    DIR* dir = opendir(dirname);
    ck_assert(dir != NULL);
    int count = 0;

    while (1)
    {
        struct dirent* dir_entry = readdir(dir);

        if (dir_entry == NULL)
            // no more entries in this directory
            break;
        else if (strcmp(dir_entry->d_name, ".") == 0
                 || strcmp(dir_entry->d_name, "..") == 0)
            // ignore '.' and '..'
            continue;
        else if (dir_entry->d_type == DT_DIR)
            // ignore subdirs
            continue;
        else
            count++;
    }

    assert(closedir(dir) == 0);

    ck_assert_int_eq(count, 1);
}


START_TEST(test_generate_session_token)
{
    /* ensure we're using PKI */
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_PKI);

    /* ensure empty state dir */
    ck_assert_int_eq(system("rm -rf /tmp/pki/*"), 0);

    // TODO: Setup auth mock to allow validuser/validpasswd
    const char* username = "validuser";
    const char* password = "validpasswd";

    /* generate the session token */
    time_t session_length = 60 * 60;
    unsigned char token[sspl_get_token_length()];
    bzero(token, sspl_get_token_length());
    sspl_generate_session_token(
        username,
        strlen(password) + 1, (const unsigned char*)password,
        session_length,
        token);

    /* verify public/private key generated as expected.  (Note: contents of
     * pub/pri key not verified.) */
    _ensure_one_file_present_in_dir("/tmp/pki/validuser");
    _ensure_one_file_present_in_dir("/tmp/pki/validuser/pri");
}
END_TEST


START_TEST(test_sign_and_verify_message)
{
    /* ensure we're using PKI */
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_PKI);

    /* ensure empty state dir */
    ck_assert_int_eq(system("rm -rf /tmp/pki/*"), 0);

    // TODO: Setup auth mock to allow validuser/validpasswd
    const char* username = "validuser";
    const char* password = "validpasswd";

    /* generate the session token */
    time_t session_length = 60 * 60;
    unsigned char token[sspl_get_token_length()];
    bzero(token, sspl_get_token_length());
    sspl_generate_session_token(
        username,
        strlen(password) + 1, (const unsigned char*)password,
        session_length,
        token);

    /* sign a message */
    const char* msg = "Hello, World!";
    unsigned char sig[sspl_get_sig_length()];
    int status = sspl_sign_message(strlen(msg), msg, username, token, sig);
    ck_assert_int_eq(status, 1);

    /* verify the signature */
    status = sspl_verify_message(strlen(msg), msg, username, sig);
    ck_assert_int_eq(status, 1);

}
END_TEST

Suite* basic_tests()
{
    Suite* s = suite_create("basic tests");

    /* Core test case */
    TCase* tc_core = tcase_create("Core");

    tcase_add_test(tc_core, test_generate_session_token);
    tcase_add_test(tc_core, test_sign_and_verify_message);
    suite_add_tcase(s, tc_core);

    return s;
}

int main()
{
    int number_failed;

    Suite* s = basic_tests();
    SRunner* sr = srunner_create(s);

    //sspl_set_conf_value("pki.keydir_path", "./foo111");
    /* TODO: For now, /tmp/pki is the pki directory.  This will change in a
     * future iteration to a user supplied directory, defaulting to
     * /var/lib/sspl/pki.
     */
    // Clear out the pki directory before starting the tests.
    assert(system("rm -rf /tmp/pki") == 0);
    sspl_sec_set_method(SSPL_SEC_METHOD_PKI);

    srunner_run_all(sr, CK_NORMAL);
    number_failed = srunner_ntests_failed(sr);
    srunner_free(sr);

    // Clear out the pki directory after running the tests.
    assert(system("rm -rf /tmp/pki") == 0);

    return (number_failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
