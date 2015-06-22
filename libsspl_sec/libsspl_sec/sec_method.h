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
    SSPL_SEC_METHOD_NONE
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
