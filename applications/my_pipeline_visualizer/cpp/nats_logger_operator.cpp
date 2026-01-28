/*
 * SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "nats_logger_operator.hpp"
#include <holoscan/core/domain/tensor.hpp>
#include <holoscan/core/domain/tensor_map.hpp>
#include <nats.h>
#include <flatbuffers/message_generated.h>
#include <flatbuffers/tensor_generated.h>
#include "create_tensor.hpp"

namespace holoscan::ops {

// RAII wrapper for NATS connection
class NatsLoggerOp::Impl {
 public:
  natsConnection* conn = nullptr;
  
  ~Impl() {
    if (conn) {
      natsConnection_Destroy(conn);
    }
  }
};

void NatsLoggerOp::setup(OperatorSpec& spec) {
  spec.input<TensorMap>("in");
  spec.output<TensorMap>("out");
  spec.param(nats_url_, "nats_url", "NATS URL", "NATS server URL",
             std::string("nats://0.0.0.0:4222"));
  spec.param(subject_, "subject", "NATS Subject", "Subject to publish to",
             std::string("data"));
  spec.param(stream_id_, "stream_id", "Stream ID", "Unique identifier for this stream",
             std::string("stream"));
}

void NatsLoggerOp::initialize() {
  Operator::initialize();
  impl_ = std::make_unique<Impl>();
  
  // Connect to NATS
  natsOptions* opts = nullptr;
  natsOptions_Create(&opts);
  natsOptions_SetURL(opts, nats_url_.get().c_str());
  natsOptions_SetSendAsap(opts, true);  // Low latency
  
  natsStatus status = natsConnection_Connect(&impl_->conn, opts);
  natsOptions_Destroy(opts);
  
  if (status != NATS_OK) {
    HOLOSCAN_LOG_ERROR("Failed to connect to NATS: {}", natsStatus_GetText(status));
    throw std::runtime_error("NATS connection failed");
  }
  
  HOLOSCAN_LOG_INFO("NATS logger connected to {} on subject '{}'", 
                    nats_url_.get(), subject_.get());
}

void NatsLoggerOp::compute(InputContext& op_input, OutputContext& op_output,
                           ExecutionContext& context) {
  // Receive tensor map
  auto tensor_map = op_input.receive<TensorMap>("in").value();
  
  // Publish to NATS (only the first tensor for simplicity)
  if (!tensor_map.empty()) {
    auto& [name, tensor] = *tensor_map.begin();
    
    try {
      // Build FlatBuffers message
      flatbuffers::FlatBufferBuilder builder(1024);
      
      // Create tensor payload
      auto tensor_fb = create_tensor_fb(builder, tensor);
      
      // Create message
      auto unique_id_fb = builder.CreateString(stream_id_.get());
      auto msg = CreateMessage(
          builder,
          unique_id_fb,
          IOType_kOutput,
          std::chrono::system_clock::now().time_since_epoch().count(),
          std::chrono::system_clock::now().time_since_epoch().count(),
          Payload_Tensor,
          tensor_fb.Union());
      
      builder.Finish(msg);
      
      // Publish (async, non-blocking)
      natsStatus status = natsConnection_Publish(
          impl_->conn,
          subject_.get().c_str(),
          builder.GetBufferPointer(),
          builder.GetSize());
      
      if (status != NATS_OK) {
        HOLOSCAN_LOG_WARN("Failed to publish: {}", natsStatus_GetText(status));
      }
    } catch (const std::exception& e) {
      HOLOSCAN_LOG_ERROR("Error serializing tensor: {}", e.what());
    }
  }
  
  // Pass through unchanged
  op_output.emit(tensor_map, "out");
}

void NatsLoggerOp::stop() {
  HOLOSCAN_LOG_INFO("NATS logger stopping");
  Operator::stop();
}

}  // namespace holoscan::ops
