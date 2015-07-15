#include "sspl_sec.h"

#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <openssl/bn.h>
#include <openssl/rsa.h>
#include <openssl/evp.h>


const int _KEY_LENGTH_BITS = 1024;  // 1024 bit encryption.

// See comment in sspl_get_token_length() for reasoning behind this number.
const int _TOKEN_LENGTH = 1000;

/* /tmp/pki is obviously a really dumb location.  This will transition to
 * /var/lib/libsspl_sec/pki shortly. */
const char* _DEFAULT_KEYDIR_PATH = "/tmp/pki";
DIR* _keydir = NULL;
const EVP_MD* _md = NULL;
const int HASH_TYPE = NID_sha256;


unsigned int sspl_get_sig_length()
{
    return _KEY_LENGTH_BITS / 8;
}

unsigned int sspl_get_token_length()
{
    /* we need enough for the private key (modulus), the public/private
     * exponent, etc and then some more bytes for the encoding.  By
     * experimentation, using 0x10001 as the public exponent, 1024 bit
     * encryption seems to require ~887 bytes, 2048 bit encryption seems to
     * require ~1679 bytes and 4096 seems to require ~3243 bytes (when encoded
     * in PEM format.)  (Not exact:  These numbers vary.)
     *
     * We should round this up.  Normally, we'd just round up to the next power
     * of two, but this would lead to an unfortunate coincidence, namely 1024
     * bit encryption would use 1024 bytes, 2048 bit encryption would use 2048
     * bytes, etc.  This could mislead people into assuming that these values
     * are the same for a reason.  So instead, we'll just round to 1000 for
     * 1024 bit encryption.
     *
     * Note: We only support 1024 bit encryption for the moment.  We purposely
     * chose a small number of bits as the key life is only expected to be
     * about an hour or so.  (We could get away with even smaller... but if we
     * go too small, we end up unable to run the signing algorithm.)
     * */
    assert(_KEY_LENGTH_BITS == 1024);
    return _TOKEN_LENGTH;
}

RSA* _read_private_key_from_token(const unsigned char* token)
{
    RSA* rsa = NULL;
    BIO* tmp = BIO_new(BIO_s_mem());
    assert(
        BIO_write(tmp, token, sspl_get_token_length())
        == sspl_get_token_length());
    assert(PEM_read_bio_RSAPrivateKey(tmp, &rsa, NULL, NULL));
    assert(BIO_free(tmp) == 1);
    return rsa;
}

void _hash_message(
    const unsigned char* msg, unsigned int msg_len,
    unsigned char* message_digest, unsigned int* message_digest_len)
{
    EVP_MD_CTX* mdctx = EVP_MD_CTX_create();
    assert(EVP_DigestInit_ex(mdctx, _md, NULL) == 1);
    assert(EVP_DigestUpdate(mdctx, msg, msg_len) == 1);
    assert(EVP_DigestFinal_ex(mdctx, message_digest, message_digest_len) == 1);
    EVP_MD_CTX_destroy(mdctx);
}

int sspl_sign_message(
    unsigned int msg_len, const unsigned char* msg,
    __attribute__((unused)) const char* username,
    const unsigned char* token,
    unsigned char* out_sig)
{
    RSA* rsa = _read_private_key_from_token(token);

    /* generate the message digest */
    unsigned char message_digest[EVP_MAX_MD_SIZE];
    unsigned int message_digest_len = 0;
    _hash_message(msg, msg_len, message_digest, &message_digest_len);

    /* sign the digest */
    bzero(out_sig, sspl_get_sig_length());
    unsigned int sig_len = 0;
    assert(
        RSA_sign(
            HASH_TYPE, message_digest, message_digest_len,
            out_sig, &sig_len, rsa)
        == 1);

    /* cleanup */
    RSA_free(rsa);

    /* sanity check - ensure we can verify the sig we just created. */
    assert(sspl_verify_message(msg_len, msg, username, out_sig) == 1);

    return 1;
}

int sspl_verify_message(
    unsigned int msg_len, const unsigned char* msg,
    const char* username,
    const unsigned char* sig)
{
    // TODO: validate username.  This is user supplied and cannot be trusted.

    /* generate the message digest (ie the hash) */
    unsigned char message_digest[EVP_MAX_MD_SIZE];
    unsigned int message_digest_len = 0;
    _hash_message(msg, msg_len, message_digest, &message_digest_len);

    /* iterate over the private keys for this user and attempt to verify the
     * message with each. */
    // TODO: use the public key rather than the private key.
    char* dirname = malloc(
                        strlen("/tmp/pki/")
                        + strlen(username)
                        + strlen("/pri")
                        + 1);
    sprintf(dirname, "/tmp/pki/%s/pri", username);
    DIR* dir = opendir(dirname);
    int ret_value = 0;

    while (1)
    {
        struct dirent* dir_entry = readdir(dir);

        if (dir_entry == NULL)
            // no more entries in this directory
            break;
        else if (strcmp(dir_entry->d_name, ".") == 0
                 || strcmp(dir_entry->d_name, "..") == 0)
            // ignore '.' and '..'
            continue;

        /* calculate full filename */
        char* fname = malloc(
                          strlen(dirname) + 1 + strlen(dir_entry->d_name) + 1);
        sprintf(fname, "%s/%s", dirname, dir_entry->d_name);
        FILE* pri_file_stream = fopen(fname, "r");
        free(fname);

        /* load rsa private key */
        RSA* rsa = NULL;
        assert(PEM_read_RSAPrivateKey(pri_file_stream, &rsa, NULL, NULL));
        fclose(pri_file_stream);

        /* attempt to verify message */
        ret_value = RSA_verify(HASH_TYPE, message_digest, message_digest_len,
                               sig, sspl_get_sig_length(), rsa);
        RSA_free(rsa);

        if (ret_value == 1)
            break;
    }

    /* cleanup */
    free(dirname);
    assert(closedir(dir) == 0);

    return ret_value;
}

/**
 * @brief                         Create directory structure for user (if it
 *                                doesn't already exist)
 */
void _ensure_user_key_dir_exists(const char* username)
{
    /* TODO: validate username. */
    DIR* pki_dir = opendir("/tmp/pki");
    assert(pki_dir != NULL);
    int status = mkdirat(dirfd(pki_dir), username, 0700);
    assert(status == 0 || errno == EEXIST);
    DIR* user_dir = fdopendir(openat(dirfd(pki_dir), username, O_DIRECTORY));
    assert(user_dir != NULL);
    status = mkdirat(dirfd(user_dir), "pri", 0700);
    assert(status == 0 || errno == EEXIST);
    DIR* user_pri_dir = fdopendir(openat(dirfd(user_dir), "pri", O_DIRECTORY));
    assert(user_pri_dir != NULL);
    closedir(user_pri_dir);
    closedir(user_dir);
    closedir(pki_dir);
}

/**
 * @breif                         Create empty files for the public and private
 *                                keys.
 * @param username                The user who we'll create the keys for.
 * @param pri_fd                  [out] The private key file descriptor will be
 *                                stored in this pointer.  The caller is
 *                                responsible for closing this file descriptor.
 * @param pub_fd                  [out] The public key file descriptor will be
 *                                stored in this pointer.  The caller is
 *                                responsible for closing this file descriptor.
 */
void _create_empty_key_files(const char* username, int* pri_fd, int* pub_fd)
{
    /* allocate string long enough to hold the filename of the private key.
     * (Which is also guaranteed to be big enough to hold the filename of the
     * public key.)
     */
    char* template = malloc(
        strlen("/tmp/pki/")
        + strlen(username)
        + strlen("/pri/XXXXXX")
        + 1);
    sprintf(template, "/tmp/pki/%s/pri/XXXXXX", username);

    /* open private key file descriptor */
    *pri_fd = mkstemp(template);
    assert(*pri_fd != -1);

    /* find location of 'pri/XXXXXX' and copy the XXXXXX overtop of pri.  (Note
     * that XXXXXX will actually be something else as filled in by mkstemp call
     * above.) */
    char* pri_ptr = template + strlen(template) - 6 - 1 - 3;
    char buf[6];
    memcpy(buf, pri_ptr + 4, 6);
    memcpy(pri_ptr, buf, 6);
    pri_ptr[6] = 0;

    /* open public key file descriptor */
    *pub_fd = open(template, O_WRONLY | O_EXCL | O_CREAT, 0600);
    assert(*pub_fd != -1);

    /* cleanup */
    free(template);
}

RSA* _create_rsa_key()
{
    BIGNUM* exponent = BN_new();
    assert(exponent != NULL);
    assert(BN_set_word(exponent, RSA_F4) == 1);
    RSA* rsa = RSA_new();
    assert(rsa != NULL);
    // TODO: set expirey time
    assert(RSA_generate_key_ex(rsa, _KEY_LENGTH_BITS, exponent, NULL) == 1);
    BN_free(exponent);
    return rsa;
}

void _write_and_close_public_key(int pub_fd, RSA* rsa)
{
    FILE* pub_file_stream = fdopen(pub_fd, "w");
    assert(PEM_write_RSAPublicKey(pub_file_stream, rsa) == 1);
    assert(fclose(pub_file_stream) == 0);
}

void _write_and_close_private_key(int pri_fd, RSA* rsa)
{
    FILE* pri_file_stream = fdopen(pri_fd, "w");
    assert(
        PEM_write_RSAPrivateKey(
            pri_file_stream, rsa, NULL, NULL, 0, NULL, NULL)
        == 1);
    assert(fclose(pri_file_stream) == 0);
}

void _copy_private_key_to_token(RSA* rsa, unsigned char* out_token)
{
    BIO* tmp = BIO_new(BIO_s_mem());
    assert(
        PEM_write_bio_RSAPrivateKey(tmp, rsa, NULL, NULL, 0, NULL, NULL) == 1);
    bzero(out_token, sspl_get_token_length());
    long len = BIO_read(tmp, out_token, sspl_get_token_length());
    assert(BIO_free(tmp) == 1);
    assert(len <= sspl_get_token_length());
}

void sspl_generate_session_token(
    const char* username,
    __attribute__((unused)) unsigned int authn_token_len,
    __attribute__((unused)) const unsigned char* authn_token,
    __attribute__((unused)) time_t session_length,
    unsigned char* out_token)
{
    /* TODO: validate username, authn_token.  These are user supplied values
     * that cannot be trusted. */

    /* TODO: check creds */

    _ensure_user_key_dir_exists(username);

    int pri_fd = -1;
    int pub_fd = -1;
    _create_empty_key_files(username, &pri_fd, &pub_fd);

    RSA* rsa = _create_rsa_key();

    _write_and_close_public_key(pub_fd, rsa);
    _write_and_close_private_key(pri_fd, rsa);

    _copy_private_key_to_token(rsa, out_token);

    /* cleanup */
    RSA_free(rsa);
}

void __attribute__((constructor)) init()
{
    const char* keydir_path = _DEFAULT_KEYDIR_PATH;
    _keydir = opendir(keydir_path);

    /* if dir doesn't exist, create it */
    if (_keydir == NULL && errno == ENOENT)
    {
        int status = mkdir(keydir_path, 0700);

        if (status != 0)
            err(errno, "Fatal: Unable to create keydir %s", keydir_path);

        _keydir = opendir(keydir_path);
    }

    /* if dir still doesn't exist, something went wrong.  abort. */
    if (!_keydir)
        err(errno, "Fatal: Unable to open keydir %s", keydir_path);

    /* ensure proper permissions on directory */
    // TODO

    /* initialize/setup openssl hashing */
    OpenSSL_add_all_digests();
    _md = EVP_get_digestbynid(HASH_TYPE);
    assert(_md);
}

void __attribute__((destructor)) fini()
{
    if (_keydir)
        closedir(_keydir);

    EVP_cleanup();
}
