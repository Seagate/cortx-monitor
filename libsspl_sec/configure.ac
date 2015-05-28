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
if test "x$DOXYGEN" = "x" ; then
    AC_MSG_ERROR([Error:  Unable to find doxygen.])
fi

AC_ARG_VAR(LETTUCE, [Path to lettuce.  Used for acceptance testing.])
AC_PATH_PROG(LETTUCE, lettuce,, $PATH:$HOME/.local/bin/)
if test "x$LETTUCE" == "x" ; then
    AC_MSG_ERROR([Error:  Unable to find lettuce.])
fi

AC_ARG_VAR(ASTYLE, [Path to astyle.  Used for C style checking.])
AC_PATH_PROG(ASTYLE, astyle)
if test "x$ASTYLE" == "x" ; then
    AC_MSG_ERROR([Error: Unable to find astyle.])
fi

AC_ARG_VAR(FLAKE8, [Path to flake8.  Used for python style checking.])
AC_PATH_PROG(FLAKE8, flake8)
if test "x$FLAKE8" == "x" ; then
    AC_MSG_ERROR([Error: Unable to find flake8.])
fi

AC_ARG_VAR(PYLINT, [Path to pylint.  Used for python style checking.])
AC_PATH_PROG(PYLINT, pylint)
if test "x$PYLINT" == "x" ; then
    AC_MSG_ERROR([Error: Unable to find pylint.])
fi


PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])


#AC_CHECK_HEADERS(ssl.h,,AC_MSG_ERROR(missing ssl.h))
#AC_CHECK_LIB(ssl, symbol_used_in_libssl,, AC_MSG_ERROR(missing libssl))

###############################################################################
# Output
###############################################################################
AC_OUTPUT(Makefile libsspl_sec/Makefile doc/Makefile tests/Makefile tests/unit/Makefile tests/acceptance/helpers/Makefile tests/acceptance/Makefile)
