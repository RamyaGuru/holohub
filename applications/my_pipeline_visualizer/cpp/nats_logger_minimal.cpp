/*
 * SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Implements NATS-based AsyncDataLoggerResource and AsyncDataLoggerBackend interface.
 *
 * DataLoggerResource Docs: https://docs.nvidia.com/holoscan/sdk-user-guide/holoscan_data_logging.html
 * Reference implementation (Console Logger in Holoscan SDK) 
 https://github.com/nvidia-holoscan/holoscan-sdk/blob/main/include/holoscan/data_loggers/async_console_logger/
 * 
 * PATTERN EXPLANATION:
 * AsyncDataLoggerResource (parent class) provides:
 *   - Automatic interception of all operator I/O via add_data_logger()
 *   - Queue management for incoming data entries
 *   - Worker thread that processes entries asynchronously
 * 
 * AsyncDataLoggerBackend defines:
 *   - HOW to process each entry (via process_data_entry)
 *   - Backend-specific initialization/shutdown
 * 
 * CUSTOMIZATION:
 * To adapt this logger for other backends (Kafka, file, database, etc.):
 *   1. Change the Impl class to connect to your backend
 *   2. AsyncDataLoggerBackend: Modify process_data_entry() to serialize/publish to your backend
 *   3. AsyncDataLoggerResource: Modify the log_*_data() methods with custom tensor logging
 */


#include "nats_logger_minimal.hpp"
#include <holoscan/core/domain/tensor.hpp>
#include <holoscan/core/domain/tensor_map.hpp>
#include <holoscan/logger/logger.hpp>
#include <nats.h>
#include <flatbuffers/message_generated.h>
#include <flatbuffers/tensor_generated.h>
#include "create_tensor.hpp"

namespace holoscan::data_loggers {

/**
 * RAII wrapper for NATS connection management
 * Contains: NATS connection handle and subject prefix
 * Cleanup: Automatically destroys NATS connection on destruction
 */
class NatsLogger::Impl {
 public:
  natsConnection* conn = nullptr;
  std::string subject_prefix;
  
  ~Impl() {
    if (conn) {
      natsConnection_Destroy(conn);
    }
  }
  
  /**
   * Connect to NATS server
   * Input Parameters:
   *   - url: NATS server URL (e.g., "nats://0.0.0.0:4222")
   * Return Value: None (throws exception on failure)
   */
  void connect(const std::string& url) {
    natsOptions* opts = nullptr;
    natsOptions_Create(&opts);
    natsOptions_SetURL(opts, url.c_str());
    natsOptions_SetSendAsap(opts, true);
    
    natsStatus status = natsConnection_Connect(&conn, opts);
    natsOptions_Destroy(opts);
    
    if (status != NATS_OK) {
      throw std::runtime_error("Failed to connect to NATS");
    }
  }
};

/**
 * Configure logger parameters
 * Input Parameters:
 *   - spec: Component specification for parameter registration
 * Return Value: None
 */
void NatsLogger::setup(ComponentSpec& spec) {
  spec.param(nats_url_, "nats_url", "NATS URL", "NATS server URL",
             std::string("nats://0.0.0.0:4222"));
  spec.param(subject_prefix_, "subject_prefix", "Subject Prefix",
             "Prefix for NATS subjects", std::string(""));
}

/**
 * Initialize NATS connection and async backend
 * Input Parameters: None
 * Return Value: None (throws exception on failure)
 */
void NatsLogger::initialize() {
  AsyncDataLoggerResource::initialize();
  
  impl_ = std::make_shared<Impl>();
  
  if (subject_prefix_.get().empty()) {
    throw std::runtime_error("subject_prefix is required");
  }
  
  impl_->subject_prefix = subject_prefix_.get();
  impl_->connect(nats_url_.get());
  
  // Set up async backend
  auto backend = std::make_shared<AsyncNatsBackend>(this);
  set_async_backend(backend);
  
  HOLOSCAN_LOG_INFO("Minimal NATS logger initialized: {}", nats_url_.get());
}

// ============================================================================
// Specialized logging methods for different data types
// These methods are required overrides from AsyncDataLoggerResource base class
// Docs: https://docs.nvidia.com/holoscan/sdk-user-guide/holoscan_data_logging.html#data-types-supported
// Implementation pattern: AsyncDataLoggerBackend (see Holoscan SDK source code)
// ============================================================================

/**
 * Log tensor data to NATS via async backend
 * Input Parameters:
 *   - tensor: Shared pointer to tensor data
 *   - unique_id: Unique identifier for the data stream
 *   - acquisition_timestamp: When data was acquired (nanoseconds)
 *   - metadata: Optional metadata dictionary
 *   - io_type: Input or output type
 *   - stream: Optional CUDA stream
 * Return Value: true if queued successfully, false otherwise
 */
bool NatsLogger::log_tensor_data(const std::shared_ptr<Tensor>& tensor,
                                        const std::string& unique_id,
                                        int64_t acquisition_timestamp,
                                        const std::shared_ptr<MetadataDictionary>& metadata,
                                        IOSpec::IOType io_type,
                                        std::optional<cudaStream_t> stream) {
  return AsyncDataLoggerResource::log_tensor_data(
      tensor, unique_id, acquisition_timestamp, metadata, io_type, stream);
}

/**
 * Log tensor map data to NATS via async backend
 * Input Parameters:
 * - tensor_map: Map of tensors to log
 * - (same as above)
 * Return Value: true if queued successfully, false otherwise
 */
bool NatsLogger::log_tensormap_data(const TensorMap& tensor_map,
                                           const std::string& unique_id,
                                           int64_t acquisition_timestamp,
                                           const std::shared_ptr<MetadataDictionary>& metadata,
                                           IOSpec::IOType io_type,
                                           std::optional<cudaStream_t> stream) {
  return AsyncDataLoggerResource::log_tensormap_data(
      tensor_map, unique_id, acquisition_timestamp, metadata, io_type, stream);
}

/**
 * Log generic data (not needed for pipeline visualizer since we only log tensor data)
 * Input Parameters:
 * - data: Generic data to log
 * - (same as above)
 * Return Value: true (always succeeds, ignores generic data)
 */
 bool NatsLogger::log_data(const std::any& data, const std::string& unique_id,
  int64_t acquisition_timestamp,
  const std::shared_ptr<MetadataDictionary>& metadata,
  IOSpec::IOType io_type,
  std::optional<cudaStream_t> stream) {
return true;  // Ignore generic data
}

/**
 * Log backend-specific data (not needed for pipeline visualizer since we only log tensor data)
 * Input Parameters:
 * - data: Backend-specific data to log
 * - (same as above)
 * Return Value: true (always succeeds, ignores backend-specific data)
 */
bool NatsLogger::log_backend_specific(const std::any& data,
                                             const std::string& unique_id,
                                             int64_t acquisition_timestamp,
                                             const std::shared_ptr<MetadataDictionary>& metadata,
                                             IOSpec::IOType io_type,
                                             std::optional<cudaStream_t> stream) {
  return true;  // Ignore backend-specific
}

// ============================================================================
// Async NATS Backend Implementation
// ============================================================================
/**
 * Implements AsyncDataLoggerResource and AsyncDataLoggerBackend interface.
 * 
 * PATTERN EXPLANATION:
 * AsyncDataLoggerResource (parent class) provides:
 *   - Automatic interception of all operator I/O via add_data_logger()
 *   - Queue management for incoming data entries
 *   - Worker thread that processes entries asynchronously
 * 
 * AsyncDataLoggerBackend defines:
 *   - HOW to process each entry (via process_data_entry)
 *   - Backend-specific initialization/shutdown
 * 
 * CUSTOMIZATION:
 * To adapt this logger for other backends (Kafka, file, database, etc.):
 *   1. Change the Impl class to connect to your backend
 *   2. Modify process_data_entry() to serialize/publish to your backend
 *   3. Keep the log_*_data() methods as-is (they just delegate to parent)
 */

/**
 * Constructor for async NATS backend
 * Input Parameters:
 *   - logger: Pointer to parent NatsLogger instance
 * Return Value: N/A (constructor)
 */
NatsLogger::AsyncNatsBackend::AsyncNatsBackend(NatsLogger* logger)
    : logger_(logger) {}

/**
 * Initialize async backend
 * Input Parameters: None
 * Return Value: true (always succeeds)
 */
bool NatsLogger::AsyncNatsBackend::initialize() {
  return true;  // Nothing special needed
}

/**
 * Shutdown async backend (cleanup handled by RAII)
 * Input Parameters: None
 * Return Value: None
 */
void NatsLogger::AsyncNatsBackend::shutdown() {
  // Cleanup handled by RAII
}

/**
 * Process and publish data entry to NATS
 * Input Parameters:
 *   - entry: Data entry containing tensor or tensor map
 * Return Value: true if published successfully, false otherwise
 */
bool NatsLogger::AsyncNatsBackend::process_data_entry(const DataEntry& entry) {
  if (!logger_->impl_->conn) {
    return false;
  }
  
  try {
    // Handle TensorData
    if (entry.type == DataEntry::Type::TensorData && entry.tensor) {
      flatbuffers::FlatBufferBuilder builder(1024);
      
      auto tensor_fb = create_tensor_fb(builder, entry.tensor);
      auto unique_id_fb = builder.CreateString(entry.unique_id);
      
      auto msg = CreateMessage(
          builder,
          unique_id_fb,
          entry.io_type == IOSpec::IOType::kInput ? IOType_kInput : IOType_kOutput,
          entry.acquisition_timestamp,
          entry.timestamp,
          Payload_Tensor,
          tensor_fb.Union());
      
      builder.Finish(msg);
      
      std::string subject = logger_->impl_->subject_prefix + ".data";
      natsConnection_Publish(
          logger_->impl_->conn,
          subject.c_str(),
          builder.GetBufferPointer(),
          builder.GetSize());
      
      return true;
    }
    
    // Handle TensorMapData
    if (entry.type == DataEntry::Type::TensorMapData && entry.tensor_map) {
      for (const auto& [name, tensor] : *entry.tensor_map) {
        flatbuffers::FlatBufferBuilder builder(1024);
        
        auto tensor_fb = create_tensor_fb(builder, tensor);
        auto unique_id_fb = builder.CreateString(entry.unique_id);
        
        auto msg = CreateMessage(
            builder,
            unique_id_fb,
            entry.io_type == IOSpec::IOType::kInput ? IOType_kInput : IOType_kOutput,
            entry.acquisition_timestamp,
            entry.timestamp,
            Payload_Tensor,
            tensor_fb.Union());
        
        builder.Finish(msg);
        
        std::string subject = logger_->impl_->subject_prefix + ".data";
        natsConnection_Publish(
            logger_->impl_->conn,
            subject.c_str(),
            builder.GetBufferPointer(),
            builder.GetSize());
      }
      return true;
    }
    
  } catch (const std::exception& e) {
    HOLOSCAN_LOG_ERROR("Error publishing: {}", e.what());
    return false;
  }
  
  return false;
}

}  // namespace holoscan::data_loggers
