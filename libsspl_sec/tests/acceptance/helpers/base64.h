#ifndef __BASE64_H__
#define __BASE64_H__

#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief                         Base64 encode some bytes.
 *
 * The caller is responsible for allocating the out_encoded_string variable
 * prior to calling this function.
 */
size_t b64encode(
    const unsigned char* bytes_to_encode, size_t bytes_to_encode_length,
    char* out_encoded_string, size_t out_encoded_string_length);

/**
 * @brief                         Calculate the required size to hold a b64
 *                                encoded string.
 *
 * Does not include the terminating 0 character.
 */
//size_t get_b64encode_length(size_t bytes_to_encode_length);

/**
 * @brief                         Base64 decode a string.
 *
 * The caller is responsible for allocating the out_decoded_bytes variable
 * prior to calling this function.
 */
void b64decode(
    const char* string_to_decode,
    unsigned char* out_decoded_bytes, size_t out_decoded_bytes_length);

/**
 * @brief                         Calculates how much size is required to store
 *                                a b64 encoded string.
 * @param raw_size                The size (in bytes) of the binary string that
 *                                is to be base64 encoded.
 * @return                        Requried buffer size for the encoded b64
 *                                string.
 *
 * Assuming the binary data you have is raw_size bytes long, then this method
 * will calculate the maximum size of that binary string when encoded into
 * base64.  Note that the actual size may be smaller by a few bytes.  This
 * assumes the output is a single line string and not split into multiple
 * lines.
 *
 * The resulting size *does* include a byte for the NULL terminator.
 */
size_t calc_max_b64_encoded_size(size_t raw_size);

//size_t get_b64decode_length(size_t bytes_to_decode_length);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif
