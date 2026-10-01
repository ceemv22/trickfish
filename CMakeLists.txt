cmake_minimum_required(VERSION 3.25)

project(trickfish LANGUAGES CXX)

add_library(trickfish_core
    cpp/src/movegen.cpp
    cpp/src/perft.cpp
    cpp/src/position.cpp
    cpp/src/search.cpp
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

include(CTest)
if(BUILD_TESTING)
    add_executable(trickfish_zobrist_test cpp/tests/zobrist.cpp)
    target_link_libraries(trickfish_zobrist_test PRIVATE trickfish_core)
    add_test(NAME zobrist_updates COMMAND trickfish_zobrist_test)
    add_executable(trickfish_search_test cpp/tests/search.cpp)
    target_link_libraries(trickfish_search_test PRIVATE trickfish_core)
    add_test(NAME search_baselines COMMAND trickfish_search_test)
endif()
