#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <getopt.h>
#include <string.h>
#include <assert.h>

#include "sspl_sec.h"
#include "sec_method.h"
#include "base64.h"

const char* DEFAULT_METHOD = "None";

struct Args
{
    const char* method;
    const char* username;
    const char* base64_session_token;
};

struct Args parse_args(int argc, char* argv[])
{
    struct Args retval;
    retval.method = DEFAULT_METHOD;
    retval.username = NULL;
    retval.base64_session_token = NULL;

    while (1)
    {
        static struct option long_options[] =
        {
            {"method", required_argument, 0, 'm' },
            {0, 0, 0, 0}
        };

        int option_index = 0;
        int c = getopt_long(argc, argv, "m:", long_options, &option_index);

        if (c == -1)
            break;

        switch (c)
        {
            case 'm':
                retval.method = optarg;
        }
    }

    if (optind + 2 != argc)
    {
        printf("Error:  Incorrect number of arguments\n");
        exit(1);
    }

    retval.username = argv[optind];
    retval.base64_session_token = argv[optind + 1];

    return retval;
}

int main(int argc, char* argv[])
{
    struct Args args = parse_args(argc, argv);

    /* set method, if necessary */
    enum sspl_sec_method method = SSPL_SEC_METHOD_NONE;

    if (strcmp(args.method, "None") == 0)
    {
    }
    //else (strcmp(args.method, "PKI") == 0)
    //{
    //    TODO
    //}
    else
    {
        fprintf(stderr, "ERROR: Unrecognized method name: %s\n", args.method);
        abort();
    }

    if (method != sspl_sec_get_method())
        sspl_sec_set_method(method);

    /* base64 decode the session token */
    unsigned char session_token[sspl_get_token_length()];
    b64decode(args.base64_session_token, session_token, sizeof(session_token));

    /* read message from stdin */
    char* message = NULL;
    size_t size = 0;

    while (1)
    {
        char buffer[1024];
        size_t bytes_read = read(STDIN_FILENO, buffer, 1024);

        if (bytes_read == 0) break;

        message = (char*)realloc(message, size + bytes_read);
        memcpy(message + size, buffer, bytes_read);
        size += bytes_read;
    }


    /* sign message */
    unsigned char sig[sspl_get_sig_length()];
    sspl_sign_message(
        size, (unsigned char*)message, args.username, session_token, sig);

    /* b64 encode sig */
    char buf[sizeof(sig) * 4 / 3 + 1 + 2 + 1];
    memset(buf, 0, sizeof(buf));
    b64encode(sig, sizeof(sig), buf, sizeof(buf));

    /* output sig */
    printf("%s\n", buf);

    /* cleanup */
    free(message);

    return 0;
}
