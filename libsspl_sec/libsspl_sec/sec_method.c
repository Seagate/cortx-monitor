#include "sec_method.h"

enum sspl_sec_method _sspl_sec_method_current = SSPL_SEC_METHOD_NONE;

enum sspl_sec_method sspl_sec_get_method()
{
    return _sspl_sec_method_current;
}
