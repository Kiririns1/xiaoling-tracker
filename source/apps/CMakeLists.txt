cmake_minimum_required(VERSION 3.5)
set(CMAKE_NINJA_FORCE_RESPONSE_FILE ON CACHE BOOL "Use response files on Windows" FORCE)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

set(PROJECT_VER "3.1.2-silent-controls")
project(xiaoling_11885)
