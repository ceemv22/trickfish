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

find_package(Threads REQUIRED)
add_library(trickfish_uci cpp/src/uci.cpp)
target_link_libraries(trickfish_uci PUBLIC trickfish_core Threads::Threads)
set_target_properties(trickfish_uci PROPERTIES CXX_EXTENSIONS NO)

add_executable(trickfish_cpp cpp/src/main.cpp)
target_link_libraries(trickfish_cpp PRIVATE trickfish_uci)

if(MSVC)
    target_compile_options(trickfish_core PRIVATE /W4 /permissive-)
    target_compile_options(trickfish_cpp PRIVATE /W4 /permissive-)
    target_compile_options(trickfish_uci PRIVATE /W4 /permissive-)
else()
    target_compile_options(trickfish_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(trickfish_cpp PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(trickfish_uci PRIVATE -Wall -Wextra -Wpedantic)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(trickfish_zobrist_test cpp/tests/zobrist.cpp)
    target_link_libraries(trickfish_zobrist_test PRIVATE trickfish_core)
    add_test(NAME zobrist_updates COMMAND trickfish_zobrist_test)
    add_executable(trickfish_search_test cpp/tests/search.cpp)
    target_link_libraries(trickfish_search_test PRIVATE trickfish_core)
    add_test(NAME search_baselines COMMAND trickfish_search_test)
    add_executable(trickfish_transposition_test cpp/tests/transposition.cpp)
    target_link_libraries(trickfish_transposition_test PRIVATE trickfish_core)
    add_test(NAME transposition_storage COMMAND trickfish_transposition_test)
    add_executable(trickfish_history_test cpp/tests/history.cpp)
    target_link_libraries(trickfish_history_test PRIVATE trickfish_core)
    add_test(NAME repetition_history COMMAND trickfish_history_test)
    add_executable(trickfish_draw_test cpp/tests/draw.cpp)
    target_link_libraries(trickfish_draw_test PRIVATE trickfish_core)
    add_test(NAME move_count_draws COMMAND trickfish_draw_test)
    add_executable(trickfish_evaluation_test cpp/tests/evaluation.cpp)
    target_link_libraries(trickfish_evaluation_test PRIVATE trickfish_core)
    add_test(NAME evaluation_terms COMMAND trickfish_evaluation_test)
    add_executable(trickfish_uci_test cpp/tests/uci.cpp)
    target_link_libraries(trickfish_uci_test PRIVATE trickfish_uci)
    add_test(NAME uci_lifecycle COMMAND trickfish_uci_test)
    set_tests_properties(uci_lifecycle PROPERTIES TIMEOUT 20)
endif()
