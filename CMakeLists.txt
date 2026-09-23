cmake_minimum_required(VERSION 3.25)

project(trickfish LANGUAGES CXX)

add_library(trickfish_core
    cpp/src/position.cpp
)

target_include_directories(trickfish_core PUBLIC cpp/include)
target_compile_features(trickfish_core PUBLIC cxx_std_23)
set_target_properties(trickfish_core PROPERTIES CXX_EXTENSIONS NO)

add_executable(trickfish_cpp cpp/src/main.cpp)
target_link_libraries(trickfish_cpp PRIVATE trickfish_core)

if(MSVC)
    target_compile_options(trickfish_core PRIVATE /W4 /permissive-)
    target_compile_options(trickfish_cpp PRIVATE /W4 /permissive-)
else()
    target_compile_options(trickfish_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(trickfish_cpp PRIVATE -Wall -Wextra -Wpedantic)
endif()
