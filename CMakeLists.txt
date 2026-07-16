cmake_minimum_required(VERSION 3.20)
project(wyss_panel_domain LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(wyss_panel_domain firmware/src/application/panel_service.cpp)
target_include_directories(wyss_panel_domain PUBLIC firmware/include)
target_compile_options(wyss_panel_domain PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_executable(domain_tests tests/domain_tests.cpp)
target_link_libraries(domain_tests PRIVATE wyss_panel_domain)
add_test(NAME domain_tests COMMAND domain_tests)
