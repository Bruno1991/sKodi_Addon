#include "mbuc_secure_copy.h"
#include <assert.h>
#include <string.h>

int main(void) {
    char buffer[16] = "abcdefgh";
    assert(mbuc_secure_copy(buffer + 2, sizeof buffer - 2, buffer, 6) == 0);
    assert(memcmp(buffer, "ababcdef", 8) == 0);
    assert(mbuc_secure_copy(buffer, 2, "four", 4) == -2);
    assert(mbuc_secure_copy(NULL, 4, "four", 4) == -1);
    assert(mbuc_secure_copy(NULL, 0, NULL, 0) == 0);
    return 0;
}
