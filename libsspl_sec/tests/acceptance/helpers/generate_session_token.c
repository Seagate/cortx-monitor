#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <getopt.h>
#include <string.h>
#include <err.h>

#include "sspl_sec.h"
#include "sec_method.h"
#include "base64.h"

const char* DEFAULT_METHOD = "None";

struct Args
{
    const char* method;
    const char* username;
    const char* password;
    time_t session_length;
};

struct Args parse_args(int argc, char* argv[])
{
    struct Args retval;
    retval.method = DEFAULT_METHOD;
    retval.username = NULL;
    retval.password = NULL;
    retval.session_length = 60 * 60; // 1h

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
    retval.password = argv[optind + 1];

    return retval;
}

int main(int argc, char* argv[])
{
    struct Args args = parse_args(argc, argv);

    /* set method */
    if (strcmp(args.method, "None") == 0)
        sspl_sec_set_method(SSPL_SEC_METHOD_NONE);
    else if (strcmp(args.method, "PKI") == 0)
        sspl_sec_set_method(SSPL_SEC_METHOD_PKI);
    else
        errx(EXIT_FAILURE, "Invalid method: '%s'", args.method);

    unsigned char session_token[sspl_get_token_length()];
    sspl_generate_session_token(
        args.username,
        strlen(args.password) + 1, (unsigned char*)args.password,
        args.session_length,
        session_token);

    char buf[sizeof(session_token) * 4 / 3 + 1 + 2 + 1];
    memset(buf, 0, sizeof(buf));
    b64encode(session_token, sspl_get_token_length(), buf, sizeof(buf));
    printf("%s\n", buf);

    return 0;
}
