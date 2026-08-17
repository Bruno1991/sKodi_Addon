#pragma once
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
int mbuc_secure_copy(void* destination, size_t destination_capacity, const void* source, size_t count);
#ifdef __cplusplus
}
#endif
