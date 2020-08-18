/*
 *
 * Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Affero General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License along
 * with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
 * about this software or licensing, please email opensource@seagate.com or
 * cortx-questions@seagate.com.
 *
 */


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
    unsigned char* token = (unsigned char*)malloc(sspl_get_token_length());
    memset(token, 0, sspl_get_token_length());
    sspl_generate_session_token(
        username, authn_token_len, authn_token,
        session_length, token);

    /* sign message */
    const char* message = "hello, world!";
    unsigned int msg_len = strlen(message) + 1;
    unsigned char* sig = (unsigned char*)malloc(sspl_get_sig_length());
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
