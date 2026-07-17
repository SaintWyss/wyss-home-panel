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

add_executable(ui_design_tests tests/ui_design_tests.cpp)
target_include_directories(ui_design_tests PRIVATE firmware/include)
target_compile_options(ui_design_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_test(NAME ui_design_tests COMMAND ui_design_tests)

set(WYSS_FIRMWARE_ENV "waveshare_esp32_s3_touch_lcd_7" CACHE STRING
    "PlatformIO environment used to locate the pinned LVGL dependency")
set(WYSS_LVGL_CANDIDATES
    "$ENV{PLATFORMIO_CORE_DIR}/libdeps/${WYSS_FIRMWARE_ENV}/lvgl"
    "${CMAKE_SOURCE_DIR}/.pio/libdeps/${WYSS_FIRMWARE_ENV}/lvgl")
unset(WYSS_LVGL_DIR)
foreach(candidate IN LISTS WYSS_LVGL_CANDIDATES)
  if(EXISTS "${candidate}/CMakeLists.txt")
    set(WYSS_LVGL_DIR "${candidate}")
    break()
  endif()
endforeach()

if(WYSS_LVGL_DIR)
  set(LV_CONF_PATH "${CMAKE_SOURCE_DIR}/firmware/include/lv_conf.h" CACHE FILEPATH
      "Wyss LVGL configuration" FORCE)
  set(LV_CONF_INCLUDE_SIMPLE ON CACHE BOOL "Use the project LVGL configuration" FORCE)
  add_subdirectory("${WYSS_LVGL_DIR}" "${CMAKE_BINARY_DIR}/lvgl" EXCLUDE_FROM_ALL)

  add_executable(
    ui_simulator
    simulator/ui_simulator.cpp
    firmware/src/adapters/lvgl_panel_view.cpp
  )
  target_include_directories(ui_simulator PRIVATE firmware/include)
  target_compile_options(ui_simulator PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(ui_simulator PRIVATE wyss_panel_domain lvgl::lvgl)

  set(WYSS_UI_MANIFEST "${CMAKE_SOURCE_DIR}/tests/fixtures/ui_visual_manifest.txt")
  if(EXISTS "${WYSS_UI_MANIFEST}")
    add_test(
      NAME ui_visual_tests
      COMMAND ui_simulator
              --output-dir "${CMAKE_BINARY_DIR}/ui-snapshots"
              --verify "${WYSS_UI_MANIFEST}"
    )
  endif()
else()
  message(STATUS "Pinned LVGL dependency not found; ui_simulator target disabled")
endif()
