""" Example libsspl_sec usage. """
import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so')


def main():
    """ Mainline. """

    # get token (ie private key) for message signing.
    username = "jsmith"
    password = "p4sswd"
    authn_token_len = len(password) + 1
    session_length = 60 * 60  # 1h
    token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())
    SSPL_SEC.sspl_generate_session_token(
        username, authn_token_len, password,
        session_length, token)

    # sign message
    message = "hello, world!"
    msg_len = len(message) + 1
    sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
    SSPL_SEC.sspl_sign_message(msg_len, message, username, token, sig)

    # do something with the message and signature here.  (ie write to a file,
    # socket, etc.)
    print "Message: '%s'" % message
    print "Signature: '%s'" % sig.raw


if __name__ == '__main__':
    main()
