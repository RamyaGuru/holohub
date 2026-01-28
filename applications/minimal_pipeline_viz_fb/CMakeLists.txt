cmake_minimum_required(VERSION 3.20)
project(minimal_pipeline_viz_fb)

# Fetch FlatBuffers
include(FetchContent)
set(FLATBUFFERS_BUILD_TESTS OFF)
set(FLATBUFFERS_BUILD_FLATC ON)
FetchContent_Declare(
  flatbuffers
  GIT_REPOSITORY https://github.com/google/flatbuffers.git
  GIT_TAG v25.9.23
)
FetchContent_MakeAvailable(flatbuffers)
list(APPEND CMAKE_MODULE_PATH "${flatbuffers_SOURCE_DIR}/CMake")

include(BuildFlatBuffers)

set(FB_SCHEMA_FILES
    "${CMAKE_CURRENT_SOURCE_DIR}/schemas/message.fbs"
    "${CMAKE_CURRENT_SOURCE_DIR}/schemas/tensor.fbs"
)

set(FLATBUFFERS_FLATC_SCHEMA_EXTRA_ARGS --python)

build_flatbuffers(
    "${FB_SCHEMA_FILES}"
    ""
    "minimal_pipeline_viz_fb_schemas"
    ""
    "${CMAKE_CURRENT_BINARY_DIR}/flatbuffers"
    ""
    ""
)

# Print path for convenience
message(STATUS "Python FlatBuffers will be at: ${CMAKE_CURRENT_BINARY_DIR}/flatbuffers")
