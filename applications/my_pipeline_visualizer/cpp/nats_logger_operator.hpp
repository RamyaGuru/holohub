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

#ifndef NATS_LOGGER_OPERATOR_HPP
#define NATS_LOGGER_OPERATOR_HPP

#include <holoscan/holoscan.hpp>
#include <memory>
#include <string>

namespace holoscan::ops {

/**
 * @brief Minimal NATS logger operator - pass-through with logging.
 *
 * This operator:
 * 1. Receives tensor data on input port
 * 2. Publishes to NATS (async, non-blocking)
 * 3. Passes data through to output port unchanged
 *
 * Usage:
 *   auto logger = make_operator<NatsLoggerOp>(
 *       "logger",
 *       Arg("nats_url", "nats://0.0.0.0:4222"),
 *       Arg("subject", "my_app.data"),
 *       Arg("stream_id", "operator.port"));
 *
 *   // Insert in pipeline:
 *   add_flow(source, logger, {{"out", "in"}});
 *   add_flow(logger, sink, {{"out", "in"}});
 */
class NatsLoggerOp : public Operator {
 public:
  HOLOSCAN_OPERATOR_FORWARD_ARGS(NatsLoggerOp)

  void setup(OperatorSpec& spec) override;
  void initialize() override;
  void compute(InputContext& op_input, OutputContext& op_output,
               ExecutionContext& context) override;
  void stop() override;

 private:
  Parameter<std::string> nats_url_;
  Parameter<std::string> subject_;
  Parameter<std::string> stream_id_;

  class Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace holoscan::ops

#endif  // NATS_LOGGER_OPERATOR_HPP
