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
