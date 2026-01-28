/*
 * SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Minimal NATS Logger using AsyncDataLoggerResource
 * - Automatic capture of all operator I/O
 * - Async publishing (non-blocking)
 * - Minimal code (~200 lines vs 565)
 */

#ifndef NATS_LOGGER_MINIMAL_HPP
#define NATS_LOGGER_MINIMAL_HPP

#include <holoscan/core/component_spec.hpp>
#include <holoscan/core/io_spec.hpp>
#include <holoscan/core/metadata.hpp>
#include <holoscan/core/resources/async_data_logger.hpp>
#include <memory>
#include <string>

namespace holoscan {
class Tensor;
class TensorMap;
}

namespace holoscan::data_loggers {

/**
 * @brief Minimal NATS logger using AsyncDataLoggerResource.
 *
 * This is a stripped-down version that keeps the benefits of:
 * - Automatic capture (DataLogger API)
 * - Async publishing (non-blocking)
 * 
 * But removes:
 * - Rate limiting
 * - Filtering
 * - Metadata subscribers
 * - Verbose logging
 *
 * IMPLEMENTATION PATTERN:
 * Follows the same AsyncDataLoggerBackend pattern as Holoscan SDK's
 * async_console_logger. See SDK source for reference implementation:
 *   include/holoscan/data_loggers/async_console_logger/
 *
 * Usage:
 *   auto logger = make_resource<NatsLogger>(
 *       "logger",
 *       Arg("nats_url", "nats://0.0.0.0:4222"),
 *       Arg("subject_prefix", "my_app"));
 *   add_data_logger(logger);  // Automatic capture!
 */
class NatsLogger : public holoscan::AsyncDataLoggerResource {
 public:
  HOLOSCAN_RESOURCE_FORWARD_ARGS_SUPER(NatsLogger, AsyncDataLoggerResource)

  NatsLogger() = default;

  void setup(ComponentSpec& spec) override;
  void initialize() override;

  bool log_data(const std::any& data, const std::string& unique_id,
                int64_t acquisition_timestamp = -1,
                const std::shared_ptr<MetadataDictionary>& metadata = nullptr,
                IOSpec::IOType io_type = IOSpec::IOType::kOutput,
                std::optional<cudaStream_t> stream = std::nullopt) override;

  bool log_tensor_data(const std::shared_ptr<Tensor>& tensor, const std::string& unique_id,
                       int64_t acquisition_timestamp = -1,
                       const std::shared_ptr<MetadataDictionary>& metadata = nullptr,
                       IOSpec::IOType io_type = IOSpec::IOType::kOutput,
                       std::optional<cudaStream_t> stream = std::nullopt) override;

  bool log_tensormap_data(const TensorMap& tensor_map, const std::string& unique_id,
                          int64_t acquisition_timestamp = -1,
                          const std::shared_ptr<MetadataDictionary>& metadata = nullptr,
                          IOSpec::IOType io_type = IOSpec::IOType::kOutput,
                          std::optional<cudaStream_t> stream = std::nullopt) override;

  bool log_backend_specific(const std::any& data, const std::string& unique_id,
                            int64_t acquisition_timestamp = -1,
                            const std::shared_ptr<MetadataDictionary>& metadata = nullptr,
                            IOSpec::IOType io_type = IOSpec::IOType::kOutput,
                            std::optional<cudaStream_t> stream = std::nullopt) override;

 private:
  class Impl;
  std::shared_ptr<Impl> impl_;

  Parameter<std::string> nats_url_;
  Parameter<std::string> subject_prefix_;

  class AsyncNatsBackend : public AsyncDataLoggerBackend {
   public:
    explicit AsyncNatsBackend(NatsLogger* logger);
    bool initialize() override;
    void shutdown() override;
    bool process_data_entry(const DataEntry& entry) override;
    bool process_large_data_entry(const DataEntry& entry) override {
      return process_data_entry(entry);  // Same handling
    }

   private:
    NatsLogger* logger_;
  };
};

}  // namespace holoscan::data_loggers

#endif  // NATS_LOGGER_MINIMAL_HPP
