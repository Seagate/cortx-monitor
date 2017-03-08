###############################################################################
# Initialize autoconf/automake
###############################################################################
AC_INIT([libsspl_sec], [1.0.0])
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
AM_PROG_CC_C_O

###############################################################################
# Dependencies checks.
###############################################################################

AC_HEADER_STDC

AC_ARG_VAR(DOXYGEN, [Path to doxygen.  Used for API documentation generation.])
AC_PATH_PROG(DOXYGEN, doxygen)
if test "x$DOXYGEN" = "x" ; then
    AC_MSG_ERROR([Error:  Unable to find doxygen.])
fi

AC_ARG_ENABLE([tests],
        [AS_HELP_STRING([--disable-tests],
                        [disable acceptance testing])],
        [], [enable_tests=yes]
)
AS_IF([test $enable_tests = "yes"],
            [AC_ARG_VAR(LETTUCE, [Path to lettuce.  Used for acceptance testing.])
             AC_PATH_PROG(LETTUCE, lettuce,, $PATH:$HOME/.local/bin/)
             if test "x$LETTUCE" == "x" ; then
                 AC_MSG_ERROR([Error:  Unable to find lettuce.])
             fi],[])

AC_ARG_VAR(ASTYLE, [Path to astyle.  Used for C style checking.])
AC_PATH_PROG(ASTYLE, astyle)
if test "x$ASTYLE" == "x" ; then
    AC_MSG_WARN([WARNING: Unable to find astyle.])
fi

# Allow optional astyle.  It's not part of centos7 or our repos, so it's not a
# requirement.  If present, it will be automatically enabled (unless the user
# specifies --without-astyle)
AC_ARG_WITH(
    [astyle],
    [AS_HELP_STRING([--with-astyle],[support style checking @<:@default=check@:>@])],
    [],
    [with_astyle=check])
AS_IF([test "x$with_astyle" != "xno"],
[
    AC_ARG_VAR(ASTYLE, [Path to astyle.  Used for C style checking.])
    AC_PATH_PROG(ASTYLE, astyle)
    if test "x$ASTYLE" == "x" ; then
        if test "x$with_astyle" != "xcheck"; then
            AC_MSG_FAILURE([--with-astyle was given, but test for astyle failed])
        fi
        AM_CONDITIONAL([HAVE_ASTYLE], [false])
    else
        AM_CONDITIONAL([HAVE_ASTYLE], [true])
    fi
],
[
    AM_CONDITIONAL([HAVE_ASTYLE], [false])
])


# Allow optional lcov.
AC_ARG_WITH(
    [lcov],
    [AS_HELP_STRING([--with-lcov],[support coverage reports @<:@default=check@:>@])],
    [],
    [with_lcov=check])
AS_IF([test "x$with_lcov" != "xno"],
[
    AC_ARG_VAR(LCOV, [Path to lcov.  Used for coverage testing.])
    AC_PATH_PROG(LCOV, lcov)
    AC_ARG_VAR(GENHTML, [Path to genhtml.  Used for coverage testing.])
    AC_PATH_PROG(GENHTML, genhtml)
    if test "x$LCOV" == "x" ; then
        if test "x$with_lcov" != "xcheck"; then
            AC_MSG_FAILURE([--with-lcov was given, but test for lcov failed])
        fi
        AM_CONDITIONAL([HAVE_LCOV], [false])
    else
        if test "x$GENHTML" == "x" ; then
            if test "x$with_lcov" != "xcheck"; then
                AC_MSG_FAILURE([--with-lcov was given, but test for genhtml failed])
            fi
            AM_CONDITIONAL([HAVE_LCOV], [false])
        else
            AM_CONDITIONAL([HAVE_LCOV], [true])
            CFLAGS="$CFLAGS -fprofile-arcs -ftest-coverage"
            CXXFLAGS="$CXXFLAGS -fprofile-arcs -ftest-coverage"
            LDFLAGS="$LDFLAGS -fprofile-arcs -ftest-coverage -lgcov"
        fi
    fi
],
[
    AM_CONDITIONAL([HAVE_LCOV], [false])
])


# Note:  This will search for either flake8 or pep8 (with precedence given to
# flake8.)  We'll take either.
AC_ARG_VAR(FLAKE8, [Path to flake8 or pep8.  Used for python style checking.])
AC_PATH_PROGS(FLAKE8, flake8 pep8)
if test "x$FLAKE8" == "x" ; then
    AC_MSG_ERROR([Error: Unable to find flake8.])
fi

PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])

AC_CHECK_HEADERS(openssl/bio.h,,AC_MSG_ERROR(missing openssl))
AC_CHECK_LIB(crypto, BIO_new,, AC_MSG_ERROR(missing openssl))


#AC_CHECK_HEADERS(ssl.h,,AC_MSG_ERROR(missing ssl.h))
#AC_CHECK_LIB(ssl, symbol_used_in_libssl,, AC_MSG_ERROR(missing libssl))

###############################################################################
# Output
###############################################################################
AC_OUTPUT(Makefile libsspl_sec/Makefile doc/Makefile tests/Makefile tests/unit/Makefile tests/acceptance/helpers/Makefile tests/acceptance/Makefile)
