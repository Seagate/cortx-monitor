#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <cmocka.h>
#include <string.h>

#include "sspl_sec.h"
#include "sec_method.h"

void test_generate_session_token(void** state)
{
    assert_int_equal(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* username = "ignored";
    const char* password = "ignored";
    time_t session_length = 60 * 60;
    unsigned char token[sspl_get_token_length()];
    sspl_generate_session_token(
        username,
        strlen(password) + 1, (const unsigned char*)password,
        session_length,
        token);

    assert_memory_equal(token, "Token", sspl_get_token_length());
}

void test_sign_message(void** state)
{
    assert_int_equal(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* message = "Hello, World!";
    const char* username = "ignored";
    const unsigned char* token = (unsigned char*)"Token";
    unsigned char sig[sspl_get_sig_length()];

    sspl_sign_message(
        strlen(message) + 1, (unsigned char*)message,
        username,
        token,
        sig);

    assert_memory_equal(sig, "None", sspl_get_sig_length());
}

void test_verify_message(void** state)
{
    assert_int_equal(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);

    const char* message = "Hello, World!";
    const char* username = "ignored";
    const unsigned char* sig = (unsigned char*)"None";

    int success = sspl_verify_message(
                      strlen(message) + 1, (unsigned char*)message,
                      username,
                      sig);

    assert_true(success);
}

int main()
{
    const UnitTest tests[] =
    {
        unit_test(test_generate_session_token),
        unit_test(test_sign_message),
        unit_test(test_verify_message)
    };

    return run_tests(tests);
}

