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


#include "base64.h"

#include <string.h>
#include <assert.h>
#include <math.h>
#include <openssl/bio.h>
#include <openssl/evp.h>
BIO_METHOD* BIO_f_base64(void);

size_t b64encode(
    const unsigned char* bytes_to_encode, size_t bytes_to_encode_length,
    char* out_encoded_string, size_t out_encoded_string_length)
{
    BIO* b64 = BIO_new(BIO_f_base64());
    BIO* mem = BIO_new(BIO_s_mem());
    BIO* bio = BIO_push(b64, mem);

    /* Do not use newlines to flush buffer */
    BIO_set_flags(bio, BIO_FLAGS_BASE64_NO_NL);

    BIO_write(b64, bytes_to_encode, bytes_to_encode_length);
    (void)BIO_flush(b64);

    int bytes_written =
        BIO_read(mem, out_encoded_string, out_encoded_string_length);
    BIO_free_all(bio);

    return bytes_written;
}


void b64decode(
    const char* string_to_decode,
    unsigned char* out_decoded_bytes, size_t out_decoded_bytes_length)
{
    BIO* b64 = BIO_new(BIO_f_base64());
    BIO* bio = BIO_new_mem_buf(
                   // Warning: cast away const for non-cost correct method.
                   (char*)string_to_decode,
                   -1);
    bio = BIO_push(b64, bio);

    /* Do not use newlines to flush buffer */
    BIO_set_flags(bio, BIO_FLAGS_BASE64_NO_NL);

    size_t length = BIO_read(bio, out_decoded_bytes, out_decoded_bytes_length);
    assert(length <= out_decoded_bytes_length);
    BIO_free_all(bio);
}

size_t calc_max_b64_encoded_size(size_t raw_size)
{
    /* b64 encoding uses 4 bytes for every 3 bytes of input.  We round that up
     * to the next whole number.  (We're cheating a little; we should use
     * ceil(raw_size * 4/3).  Instead we use integer division and add one.
     * This will be slightly wrong if the raw_size is a multiple of three, in
     * which case, we'll report an extra byte.  That's ok.
     *
     * We then add 2 more bytes as b64 encoding adds 0,1 or 2 padding
     * characters ('=') depending on the length.  We assume a worst case
     * scenario of 2.
     *
     * Finally, we add one more byte for the null terminator.
     */
    return raw_size * 4 / 3 + 1 + 2 + 1;
}
