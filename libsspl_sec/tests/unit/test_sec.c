#include <stdlib.h>
#include <check.h>
#include <string.h>

#include "sspl_sec.h"
#include "sec_method.h"

START_TEST(test_generate_session_token)
{
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* username = "ignored";
    const char* password = "ignored";
    time_t session_length = 60 * 60;
    unsigned char token[sspl_get_token_length()];
    sspl_generate_session_token(
        username,
        strlen(password) + 1, (const unsigned char*)password,
        session_length,
        token);

    ck_assert(memcmp(token, "Token", sspl_get_token_length()) == 0);
}
END_TEST

START_TEST(test_sign_message)
{
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* message = "Hello, World!";
    const char* username = "ignored";
    const unsigned char* token = (unsigned char*)"Token";
    unsigned char sig[sspl_get_sig_length()];

    sspl_sign_message(
        strlen(message) + 1, (unsigned char*)message,
        username,
        token,
        sig);

    ck_assert(memcmp(sig, "None", sspl_get_sig_length()) == 0);
}
END_TEST

START_TEST(test_verify_message)
{
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* message = "Hello, World!";
    const char* username = "ignored";
    const unsigned char* sig = (unsigned char*)"None";

    int success = sspl_verify_message(
                      strlen(message) + 1, (unsigned char*)message,
                      username,
                      sig);

    ck_assert(success);
}
END_TEST

Suite* basic_tests()
{
    Suite* s = suite_create("basic tests");

    /* Core test case */
    TCase* tc_core = tcase_create("Core");

    tcase_add_test(tc_core, test_generate_session_token);
    tcase_add_test(tc_core, test_sign_message);
    tcase_add_test(tc_core, test_verify_message);
    suite_add_tcase(s, tc_core);

    return s;
}

int main()
{
    int number_failed;

    Suite* s = basic_tests();
    SRunner* sr = srunner_create(s);

    srunner_run_all(sr, CK_NORMAL);
    number_failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (number_failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}

