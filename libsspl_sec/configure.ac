###############################################################################
# Initialize autoconf/automake
###############################################################################
AC_INIT([libsspl_sec], [0.0.1])
AC_CONFIG_SRCDIR([libsspl_sec/sspl_sec.h])
AM_INIT_AUTOMAKE([-Wall -Werror foreign tar-ustar])

###############################################################################
# Setup compiler and flags
###############################################################################
AC_LANG_C
AC_PROG_CC
AC_PROG_MAKE_SET
AC_PROG_INSTALL
AM_PROG_AR
AC_PROG_LIBTOOL
LT_INIT

###############################################################################
# Dependencies checks.
###############################################################################

AC_HEADER_STDC

AC_ARG_VAR(DOXYGEN, [Path to doxygen.  Used for API documentation generation.])
AC_PATH_PROG(DOXYGEN, doxygen)

#AC_CHECK_HEADERS(ssl.h,,AC_MSG_ERROR(missing ssl.h))
#AC_CHECK_LIB(ssl, symbol_used_in_libssl,, AC_MSG_ERROR(missing libssl))

###############################################################################
# Output
###############################################################################
AC_OUTPUT(Makefile libsspl_sec/Makefile doc/Makefile)
