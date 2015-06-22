#include "sec_method.h"

#include <stdlib.h>

enum sspl_sec_method _sspl_sec_method_current = SSPL_SEC_METHOD_NONE;

enum sspl_sec_method sspl_sec_get_method()
{
    return _sspl_sec_method_current;
}

void sspl_sec_set_method(enum sspl_sec_method new_method)
{
    abort();
}
