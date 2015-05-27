#include "sspl_sec.h"

#include <assert.h>

unsigned int sspl_get_sig_length()
{
    assert(0 && "NYI");
}

unsigned int sspl_get_token_length()
{
    assert(0 && "NYI");
}

int sspl_sign_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* token,
    unsigned char* out_sig)
{
    assert(0 && "NYI");
}

int sspl_verify_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* sig)
{
    assert(0 && "NYI");
}

void sspl_generate_session_token(
    const char* username,
    unsigned int authn_token_len, const unsigned char* authn_token,
    time_t session_length,
    unsigned char* out_token)
{
    assert(0 && "NYI");
}
