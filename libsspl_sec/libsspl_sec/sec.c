#include "sspl_sec.h"
#include "sec_method.h"

#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <dlfcn.h>

void* _sspl_sec_lib_handle = NULL;

void __attribute__((destructor)) sspl_sec_fini(void)
{
    dlclose(_sspl_sec_lib_handle);
}

void __attribute__((constructor)) sspl_sec_init(void)
{
    if (_sspl_sec_lib_handle != NULL)
        sspl_sec_fini();

    switch (sspl_sec_get_method())
    {
        case SSPL_SEC_METHOD_NONE:
            _sspl_sec_lib_handle = dlopen("sspl_none.so.0", RTLD_NOW);
            break;

        case SSPL_SEC_METHOD_PKI:
            _sspl_sec_lib_handle = dlopen("sspl_pki.so.0", RTLD_NOW);
            break;

        default:
            fprintf(
                stderr, "ERROR: unable to interpret default signing method\n");
            abort();
    }

    if (_sspl_sec_lib_handle == NULL)
    {
        fprintf(
            stderr,
            "ERROR: A problem occurred while attempting "
            "to open sspl method module: %s\n",
            dlerror());
        abort();
    }
}

unsigned int sspl_get_sig_length()
{
    typedef unsigned int (*SSPL_GET_SIG_LENGTH_FN_PTR)();
    SSPL_GET_SIG_LENGTH_FN_PTR func_ptr = NULL;
    func_ptr = (SSPL_GET_SIG_LENGTH_FN_PTR)dlsym(
                   _sspl_sec_lib_handle,
                   __FUNCTION__);
    return (*func_ptr)();
}

unsigned int sspl_get_token_length()
{
    typedef unsigned int (*SSPL_GET_TOKEN_LENGTH_FN_PTR)();
    SSPL_GET_TOKEN_LENGTH_FN_PTR func_ptr = NULL;
    func_ptr = (SSPL_GET_TOKEN_LENGTH_FN_PTR)dlsym(
                   _sspl_sec_lib_handle,
                   __FUNCTION__);
    return (*func_ptr)();
}

int sspl_sign_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* token,
    unsigned char* out_sig)
{
    typedef int (*SSPL_SIGN_MESSAGE_FN_PTR)(
        unsigned int, const unsigned char*, const char*,
        const unsigned char*, unsigned char*);
    SSPL_SIGN_MESSAGE_FN_PTR func_ptr = NULL;
    func_ptr = (SSPL_SIGN_MESSAGE_FN_PTR)dlsym(
                   _sspl_sec_lib_handle,
                   __FUNCTION__);
    return (*func_ptr)(msg_len, msg, username, token, out_sig);
}

int sspl_verify_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* sig)
{
    typedef int (*SSPL_VERIFY_MESSAGE_FN_PTR)(
        unsigned int, const unsigned char*, const char*, const unsigned char*);
    SSPL_VERIFY_MESSAGE_FN_PTR func_ptr = NULL;
    func_ptr = (SSPL_VERIFY_MESSAGE_FN_PTR)dlsym(
                   _sspl_sec_lib_handle,
                   __FUNCTION__);
    return (*func_ptr)(msg_len, msg, username, sig);
}

void sspl_generate_session_token(
    const char* username,
    unsigned int authn_token_len, const unsigned char* authn_token,
    time_t session_length,
    unsigned char* out_token)
{
    typedef void (*SSPL_GENERATE_SESSION_TOKEN_FN_PTR)(
        const char*, unsigned int, const unsigned char*,
        time_t, unsigned char*);
    SSPL_GENERATE_SESSION_TOKEN_FN_PTR func_ptr = NULL;
    func_ptr = (SSPL_GENERATE_SESSION_TOKEN_FN_PTR)dlsym(
                   _sspl_sec_lib_handle,
                   __FUNCTION__);
    return (*func_ptr)(
               username, authn_token_len, authn_token,
               session_length, out_token);
}
