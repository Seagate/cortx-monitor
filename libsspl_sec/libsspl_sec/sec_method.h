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


#ifndef __SSPL_SEC_METHOD_H__
#define __SSPL_SEC_METHOD_H__

#ifdef __cplusplus
extern "C" {
#endif


/**
 * @internal
 *
 * The functions contained within are used internally only to switch the
 * underlying signing method.  They *could* be used by external programs, but
 * it probably doesn't make much sense to do so, since then other programs that
 * used this library wouldn't be using the same method.
 *
 * This header file is not installed, so is not visible to the end user.
 */

enum sspl_sec_method
{
    SSPL_SEC_METHOD_NONE,
    SSPL_SEC_METHOD_PKI
};

/**
 * @brief                         Retrieve the method currently in use.
 */
enum sspl_sec_method sspl_sec_get_method();

/**
 * @brief                         Switches the signing/verification method.
 *
 * WARNING:  Do not use this unless you know what you're doing.
 *
 * This method switches libsspl_sec to use a different signing/verification
 * method.  This will make your program incompatible with other programs that
 * also use libsspl_sec unless they also call this function.  In general, do
 * not use this.
 */
void sspl_sec_set_method(enum sspl_sec_method new_method);


#ifdef __cplusplus
}  // extern "C"
#endif

#endif
