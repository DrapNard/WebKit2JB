cmake_minimum_required(VERSION 3.16)
project(webkit2jb_bridge C)

option(W2JB_BUILD_HORIZON "Build the libnx homebrew static library" OFF)
option(W2JB_BUILD_TESTS "Build deterministic bridge tests" ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

set(W2JB_COMMON
    src/core/bridge.c
    src/memory/memory_policy.c
    src/core/memory_policy_contract.c
    src/relay/relay.c
    src/protocol/protocol.c
    adapters/ns2jb-compatible/ns2jb_compat.c)

if(W2JB_BUILD_HORIZON)
    if(NOT DEFINED ENV{DEVKITPRO})
        message(FATAL_ERROR "DEVKITPRO is required for W2JB_BUILD_HORIZON")
    endif()
    add_library(webkit2jb_bridge STATIC
        ${W2JB_COMMON}
        backends/mock/backend_mock.c
        backends/horizon-homebrew/backend_horizon.c
        backends/horizon-homebrew/memory_horizon.c)
    target_compile_definitions(webkit2jb_bridge PRIVATE W2JB_BUILD_HORIZON=1)
    target_include_directories(webkit2jb_bridge PUBLIC include adapters/ns2jb-compatible PRIVATE src/core
        "$ENV{DEVKITPRO}/libnx/include")
    target_compile_options(webkit2jb_bridge PRIVATE -Wall -Wextra -Werror
        -march=armv8-a -mtune=cortex-a57 -mtp=soft -fPIE -D__SWITCH__)

    find_program(W2JB_NACPTOOL nacptool HINTS "$ENV{DEVKITPRO}/tools/bin")
    find_program(W2JB_ELF2NRO elf2nro HINTS "$ENV{DEVKITPRO}/tools/bin")
    if(NOT W2JB_NACPTOOL OR NOT W2JB_ELF2NRO)
        message(FATAL_ERROR "nacptool and elf2nro are required to package the Horizon NRO")
    endif()
    add_executable(w2jb-horizon-demo examples/horizon_bridge_demo.c)
    set_target_properties(w2jb-horizon-demo PROPERTIES SUFFIX ".elf")
    target_include_directories(w2jb-horizon-demo PRIVATE include "$ENV{DEVKITPRO}/libnx/include")
    target_compile_options(w2jb-horizon-demo PRIVATE -Wall -Wextra -Werror
        -march=armv8-a -mtune=cortex-a57 -mtp=soft -fPIE -D__SWITCH__)
    target_link_options(w2jb-horizon-demo PRIVATE
        -march=armv8-a -mtune=cortex-a57 -mtp=soft -fPIE
        "-specs=$ENV{DEVKITPRO}/libnx/switch.specs" -Wl,--gc-sections)
    target_link_directories(w2jb-horizon-demo PRIVATE "$ENV{DEVKITPRO}/libnx/lib")
    target_link_libraries(w2jb-horizon-demo PRIVATE webkit2jb_bridge nx)

    set(W2JB_NACP "${CMAKE_CURRENT_BINARY_DIR}/w2jb-horizon-demo.nacp")
    set(W2JB_NRO "${CMAKE_CURRENT_BINARY_DIR}/w2jb-horizon-demo.nro")
    add_custom_command(OUTPUT "${W2JB_NACP}"
        COMMAND "${W2JB_NACPTOOL}" --create "WebKit2JB Bridge Demo" "WebKit2JB Lab" "0.1.0" "${W2JB_NACP}"
        DEPENDS w2jb-horizon-demo
        VERBATIM)
    add_custom_command(OUTPUT "${W2JB_NRO}"
        COMMAND "${W2JB_ELF2NRO}" "$<TARGET_FILE:w2jb-horizon-demo>" "${W2JB_NRO}" "--nacp=${W2JB_NACP}"
        DEPENDS "${W2JB_NACP}" w2jb-horizon-demo
        VERBATIM)
    add_custom_target(w2jb-horizon-nro ALL DEPENDS "${W2JB_NRO}")
else()
    set(W2JB_LINUX_SOURCES
        ${W2JB_COMMON}
        backends/mock/backend_mock.c
        backends/linux/backend_linux.c
        backends/linux/memory_linux.c)
    add_library(webkit2jb_bridge STATIC ${W2JB_LINUX_SOURCES})
    add_library(webkit2jb_bridge_shared SHARED ${W2JB_LINUX_SOURCES})
    set_target_properties(webkit2jb_bridge_shared PROPERTIES
        OUTPUT_NAME webkit2jb_bridge VERSION 1.0.0 SOVERSION 1
        POSITION_INDEPENDENT_CODE ON)
    target_include_directories(webkit2jb_bridge PUBLIC include adapters/ns2jb-compatible PRIVATE src/core)
    target_include_directories(webkit2jb_bridge_shared PUBLIC include adapters/ns2jb-compatible PRIVATE src/core)
    target_compile_options(webkit2jb_bridge PRIVATE -Wall -Wextra -Werror
        -fno-common -fstack-protector-strong)
    target_compile_options(webkit2jb_bridge_shared PRIVATE -Wall -Wextra -Werror
        -fno-common -fstack-protector-strong -fPIC)
    target_link_options(webkit2jb_bridge INTERFACE -Wl,-z,noexecstack -Wl,-z,relro -Wl,-z,now)
    target_link_options(webkit2jb_bridge_shared PRIVATE -Wl,-z,noexecstack -Wl,-z,relro -Wl,-z,now)

    add_executable(w2jb-bridge-demo examples/bridge_demo.c)
    target_link_libraries(w2jb-bridge-demo PRIVATE webkit2jb_bridge)
    if(W2JB_BUILD_TESTS)
        enable_testing()
        add_executable(w2jb-bridge-tests tests/test_bridge.c)
        target_link_libraries(w2jb-bridge-tests PRIVATE webkit2jb_bridge)
        add_test(NAME bridge-contract COMMAND w2jb-bridge-tests)
        add_test(NAME bridge-demo COMMAND w2jb-bridge-demo)
        add_test(NAME no-rwx-load-segment
            COMMAND ${CMAKE_COMMAND} -DPROGRAM=$<TARGET_FILE:w2jb-bridge-demo>
                    -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/check_no_rwx.cmake)
        add_test(NAME no-rwx-test-segment
            COMMAND ${CMAKE_COMMAND} -DPROGRAM=$<TARGET_FILE:w2jb-bridge-tests>
                    -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/check_no_rwx.cmake)
        add_test(NAME no-rwx-shared-library
            COMMAND ${CMAKE_COMMAND} -DPROGRAM=$<TARGET_FILE:webkit2jb_bridge_shared>
                    -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/check_no_rwx.cmake)
    endif()
endif()
