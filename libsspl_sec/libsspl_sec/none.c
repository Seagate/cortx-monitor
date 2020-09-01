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

