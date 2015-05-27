#ifndef __SSPL_SEC_H__
#define __SSPL_SEC_H__

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @mainpage                      libsspl_sec Documentation
 *
 * @section intro                 Introduction
 *
 * libsspl_sec is used to sign and verify messages throughout sspl.  It does
 * not currently handle encryption of messages.  (The assumption is that either
 * the messages don't require encryption, or that the transport layer will
 * handle it.)
 *
 * See the Examples section for sample usage.
 */

/**
 * @example examples/c/01_message_creator.c
 *
 * Shows how to create and sign a message.
 */

/**
 * @example examples/c/02_message_consumer.c
 *
 * Shows how to verify a message is properly signed.
 */

/**
 * @file
 *
 * @brief                         Functions for libsspl_sec.
 *
 * This functions in this module are used to sign and verify messages used
 * throughout sspl.
 */

#include <time.h>

/**
 * @brief                         Get length of a message signature, in bytes.
 *
 * @return                        Length of a message signature.
 */
unsigned int sspl_get_sig_length();

/**
 * @brief                         Get length of message signing tokens, in
 *                                bytes.
 *
 * @return                        Length of message signing tokens.
 */
unsigned int sspl_get_token_length();

/**
 * @brief                         Sign the specified message.
 *
 * @param msg_len                 Length of msg, in bytes.
 * @param msg                     The message to sign.  Can be binary.
 * @param username                The user to sign the message as.  Typically,
 *                                this is ignored.
 * @param token                   The token to use to sign the message.  (For
 *                                the PKI method, this would be the private
 *                                key.)  It is assumed that this buffer is
 *                                sspl_get_token_length() bytes long.
 * @param out_sig                 Output parameter.  The resulting signature
 *                                will be stored into the memory location
 *                                pointed to by out_sig.  It is assumed that
 *                                this buffer is sspl_get_sig_length() bytes long.
 *                                The caller is responsible for allocating and
 *                                freeing this memory.
 * @return                        Success/failure.  Upon failure, call ??? TODO
 */
int sspl_sign_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* token,
    unsigned char* out_sig);

/**
 * @brief                         Verify the message has a valid signature.
 *
 * @param msg_len                 Length of msg, in bytes.
 * @param msg                     The message to verify.  Can be binary.
 * @param username                The user to verify the message as.
 * @param sig                     The message signature.  It is assumed that
 *                                this buffer is sspl_get_sig_length() bytes long.
 * @return                        Success/failure.  Upon failure, call ??? TODO
 */
int sspl_verify_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* sig);

/**
 * @brief                         Generate a temporary session token.
 *
 * The token is used to sign messages.
 *
 * This method doesn't do the token creation itself.  Instead, it requests the
 * key_manager (via a unix socket) to do so.
 *
 * @param username                The user to generate the session token for.
 * @param authn_token_len         The length of authn_token, in bytes (incl the
 *                                0 terminator for strings.)
 * @param authn_token             The authentication token that proves the
 *                                user's identity.  Probably a password.
 * @param session_length          How long the session token should be valid
 *                                for.  Specified in seconds.  (ie for a 1 hour
 *                                session key, use 60*60=3600 for this
 *                                parameter.)
 * @param out_token               The resulting session token will be placed
 *                                into the memory pointed to by out_token.  It
 *                                is assumed that this memory buffer is
 *                                sspl_get_token_length() bytes long.
 */
void sspl_generate_session_token(
    const char* username,
    unsigned int authn_token_len, const unsigned char* authn_token,
    time_t session_length,
    unsigned char* out_token);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif
