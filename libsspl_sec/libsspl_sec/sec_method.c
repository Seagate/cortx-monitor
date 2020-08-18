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


#include "sec_method.h"

#include <stdlib.h>

enum sspl_sec_method _sspl_sec_method_current = SSPL_SEC_METHOD_NONE;

enum sspl_sec_method sspl_sec_get_method()
{
    return _sspl_sec_method_current;
}

void sspl_sec_set_method(enum sspl_sec_method new_method)
{
    _sspl_sec_method_current = new_method;
    sspl_sec_init();
}
