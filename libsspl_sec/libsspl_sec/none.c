#include "sspl_sec.h"

#include <stdlib.h>
#include <string.h>

const char* _SIG = "None";
const char* _TOKEN = "Token";

const int FALSE = 0;
const int TRUE = 1;

unsigned int sspl_get_sig_length()
{
    return strlen(_SIG);
}

unsigned int sspl_get_token_length()
{
    return strlen(_TOKEN);
}

int sspl_sign_message(
    __attribute__((unused)) unsigned int msg_len,
    __attribute__((unused)) const unsigned char* msg,
    __attribute__((unused)) const char* username,
    const unsigned char* token,
    unsigned char* out_sig)
{
    /* ensure token == _TOKEN */
    if (memcmp(token, _TOKEN, sspl_get_token_length() != 0))
        return FALSE;

    memcpy(out_sig, _SIG, sspl_get_sig_length());
    return TRUE;
}

int sspl_verify_message(
    __attribute__((unused)) unsigned int msg_len,
    __attribute__((unused)) const unsigned char* msg,
    __attribute__((unused)) const char* username,
    const unsigned char* sig)
{
    return memcmp(sig, _SIG, sspl_get_sig_length()) == 0;
}

void sspl_generate_session_token(
    __attribute__((unused)) const char* username,
    __attribute__((unused)) unsigned int authn_token_len,
    __attribute__((unused)) const unsigned char* authn_token,
    __attribute__((unused)) time_t session_length,
    __attribute__((unused)) unsigned char* out_token)
{
    memcpy(out_token, _TOKEN, sspl_get_token_length());
}

