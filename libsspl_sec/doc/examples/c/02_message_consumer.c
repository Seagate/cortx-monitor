#include <string.h>
#include <stdio.h>
#include <sspl_sec.h>

int main()
{
    const char* username = "jsmith";
    const char* message = "hello, world!";
    const unsigned char* sig =
        (const unsigned char*)"obviously invalid signature";
    int valid_sig =
        sspl_verify_message(
            strlen(message) + 1,
            (const unsigned char*)message,
            username,
            sig
        );

    if (valid_sig)
        printf("sig ok\n");
    else
        printf("bad sig\n");
}
