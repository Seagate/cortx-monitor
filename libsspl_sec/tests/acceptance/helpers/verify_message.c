#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <getopt.h>
#include <string.h>

#include "sspl_sec.h"
#include "base64.h"


const char* DEFAULT_METHOD = "None";

struct Args
{
    const char* method;
    const char* username;
    const char* base64_sig;
};

struct Args parse_args(int argc, char* argv[])
{
    struct Args retval;
    retval.method = DEFAULT_METHOD;
    retval.username = NULL;
    retval.base64_sig = NULL;

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
    retval.base64_sig = argv[optind + 1];

    return retval;
}

int main(int argc, char* argv[])
{
    struct Args args = parse_args(argc, argv);

    /* base64 decode the sig */
    unsigned char sig[sspl_get_sig_length()];
    b64decode(args.base64_sig, sig, sizeof(sig));

    /* read message from stdin */
    char* message = NULL;
    size_t size = 0;

    while (1)
    {
        char buffer[1024];
        size_t bytes_read = read(STDIN_FILENO, buffer, 1024);

        if (bytes_read == 0) break;

        message = realloc(message, size + bytes_read);
        memcpy(message + size, buffer, bytes_read);
        size += bytes_read;
    }

    /* verify message signature */
    int status = sspl_verify_message(
                     strlen(message) + 1, (unsigned char*)message,
                     args.username,
                     sig);

    /* cleanup */
    free(message);

    if (status == 1)
        exit(0);
    else
        exit(1);
}
