AM_CFLAGS=-I$(top_srcdir)/libsspl_sec -Wall -Wextra -Werror
LDADD=-lcrypto $(top_builddir)/libsspl_sec/libsspl_sec.la

noinst_PROGRAMS=generate_session_token sign_message verify_message

generate_session_token_SOURCES=generate_session_token.c base64.c base64.h
sign_message_SOURCES=sign_message.c base64.c base64.h
verify_message_SOURCES=verify_message.c base64.c base64.h

MOSTLYCLEANFILES=*.gcno *.gcda
