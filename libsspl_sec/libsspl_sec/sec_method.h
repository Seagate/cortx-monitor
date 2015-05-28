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
 */

enum sspl_sec_method
{
    SSPL_SEC_METHOD_NONE
};

/**
 * @brief                         Retrieve the method currently in use.
 */
enum sspl_sec_method sspl_sec_get_method();


#ifdef __cplusplus
}  // extern "C"
#endif

#endif
