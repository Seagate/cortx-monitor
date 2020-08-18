/*
 *
 * Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Affero General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License along
 * with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
 * about this software or licensing, please email opensource@seagate.com or
 * cortx-questions@seagate.com.
 *
 */


#include <stdlib.h>
#include <stdio.h>
#include <check.h>
#define __USE_GNU
#include <dlfcn.h>
#include <link.h>

#include "sec_method.h"

extern void* _sspl_sec_lib_handle;

char* _get_soname_from_dlopen_handle(void* handle)
{
    struct link_map* map;
    dlinfo(handle, RTLD_DI_LINKMAP, &map);
    ck_assert(map->l_name != NULL);
    char* last_slash_ptr = strrchr(map->l_name, '/');
    ck_assert(last_slash_ptr != NULL);
    return last_slash_ptr + 1;
}

START_TEST(test_sspl_sec_get_method)
{
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);
    ck_assert_str_eq(
        _get_soname_from_dlopen_handle(_sspl_sec_lib_handle),
        "sspl_none.so.0");
}
END_TEST

START_TEST(test_sspl_sec_set_method)
{
    /* attempt to set the method to pki */
    sspl_sec_set_method(SSPL_SEC_METHOD_PKI);
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_PKI);
    ck_assert_str_eq(
        _get_soname_from_dlopen_handle(_sspl_sec_lib_handle),
        "sspl_pki.so.0");

    /* reset the method back to the default of 'none' */
    sspl_sec_set_method(SSPL_SEC_METHOD_NONE);
    ck_assert_int_eq(sspl_sec_get_method(), SSPL_SEC_METHOD_NONE);
    ck_assert_str_eq(
        _get_soname_from_dlopen_handle(_sspl_sec_lib_handle),
        "sspl_none.so.0");
}
END_TEST

Suite* sec_method_tests()
{
    Suite* s = suite_create("sec_method tests");

    TCase* tc_core = tcase_create("Core");
    tcase_add_test(tc_core, test_sspl_sec_get_method);
    tcase_add_test(tc_core, test_sspl_sec_set_method);
    suite_add_tcase(s, tc_core);

    return s;
}

int main()
{
    int number_failed;

    Suite* s = sec_method_tests();
    SRunner* sr = srunner_create(s);

    srunner_run_all(sr, CK_NORMAL);
    number_failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (number_failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
