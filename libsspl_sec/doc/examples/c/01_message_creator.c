#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sspl_sec.h>

int main()
{
    /* get token (ie private key) for message signing. */
    const char* username = "jsmith";
    const char* password = "p4sswd";
    unsigned int authn_token_len = strlen(password) + 1;
    const unsigned char* authn_token = (const unsigned char*)password;
    time_t session_length = 60 * 60;  // 1h
    unsigned char* token = malloc(sspl_get_token_length());
    memset(token, 0, sspl_get_token_length());
    sspl_generate_session_token(
        username, authn_token_len, authn_token,
        session_length, token);

    /* sign message */
    const char* message = "hello, world!";
    unsigned int msg_len = strlen(message) + 1;
    unsigned char* sig = malloc(sspl_get_sig_length());
    memset(sig, 0, sspl_get_sig_length());
    sspl_sign_message(
        msg_len, (const unsigned char*)message, username,
        token, sig);

    /* do something with the message and signature here.  (ie write to a file,
     * socket, etc.)  */
    printf("Message: '%s'\n", message);
    printf("Signature: '%s'\n", (const char*)sig);

    /* cleanup */
    free(token);
    free(sig);
}
