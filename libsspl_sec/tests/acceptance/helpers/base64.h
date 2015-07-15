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

//size_t get_b64decode_length(size_t bytes_to_decode_length);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif
