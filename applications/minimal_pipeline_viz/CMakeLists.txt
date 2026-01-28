cmake_minimum_required(VERSION 3.20)
project(minimal_pipeline_viz NONE)

find_package(holoscan REQUIRED CONFIG)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Install Python dependencies from requirements.txt
add_custom_target(install_python_deps ALL)
add_custom_command(
    TARGET install_python_deps
    COMMAND ${Python3_EXECUTABLE} -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
    COMMENT "Installing Python dependencies from requirements.txt..."
)
