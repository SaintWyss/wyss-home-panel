cmake_minimum_required(VERSION 3.20)
project(wyss_panel_domain LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(
  wyss_panel_domain
  firmware/src/application/panel_service.cpp
  firmware/src/protocol/envelope_v2.cpp
)
target_include_directories(wyss_panel_domain PUBLIC firmware/include)
target_compile_definitions(wyss_panel_domain PRIVATE WYSS_ENABLE_PROTOCOL_V2=1)
target_compile_options(wyss_panel_domain PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_executable(domain_tests tests/domain_tests.cpp)
target_link_libraries(domain_tests PRIVATE wyss_panel_domain)
add_test(NAME domain_tests COMMAND domain_tests)

add_executable(protocol_fixture_tests tests/protocol_fixture_tests.cpp)
target_compile_definitions(protocol_fixture_tests PRIVATE WYSS_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
target_compile_options(protocol_fixture_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME protocol_fixture_tests COMMAND protocol_fixture_tests)

add_executable(protocol_v2_fixture_tests tests/protocol_v2_fixture_tests.cpp)
target_compile_definitions(protocol_v2_fixture_tests PRIVATE WYSS_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
target_compile_options(protocol_v2_fixture_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_link_libraries(protocol_v2_fixture_tests PRIVATE wyss_panel_domain)
add_test(NAME protocol_v2_fixture_tests COMMAND protocol_v2_fixture_tests)
