/*
 * Copyright 2019 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#pragma once

#include <memory>
#include <string>

#include "module.h"

namespace bluetooth {
namespace shim {

struct AdvertisingReport {
  uint16_t extended_event_type;
  std::string string_address;
  uint8_t address_type;
  int8_t rssi;
  uint8_t* data;
  size_t len;
};

struct DirectedAdvertisingReport : public AdvertisingReport {
  DirectedAdvertisingReport(AdvertisingReport report) : AdvertisingReport(report) {}
  uint8_t directed_advertising_type;
};

struct ExtendedAdvertisingReport : public DirectedAdvertisingReport {
  ExtendedAdvertisingReport(AdvertisingReport report) : DirectedAdvertisingReport(report) {}
};

class Scanning : public bluetooth::Module {
 public:
  using AdvertisingReportCallback = std::function<void(AdvertisingReport report)>;
  using DirectedAdvertisingReportCallback = std::function<void(DirectedAdvertisingReport report)>;
  using ExtendedAdvertisingReportCallback = std::function<void(ExtendedAdvertisingReport report)>;
  using ScanningTimeoutCallback = std::function<void()>;

  Scanning() = default;
  ~Scanning() = default;

  void StartScanning(bool set_active, AdvertisingReportCallback advertising_callback,
                     DirectedAdvertisingReportCallback directed_advertisting_callback,
                     ExtendedAdvertisingReportCallback extended_advertising_callback,
                     ScanningTimeoutCallback timeout_callback);
  void StopScanning();

  static const ModuleFactory Factory;

 protected:
  void ListDependencies(ModuleList* list) override;  // Module
  void Start() override;                             // Module
  void Stop() override;                              // Module
  std::string ToString() const override;             // Module

 private:
  struct impl;
  std::unique_ptr<impl> pimpl_;
  DISALLOW_COPY_AND_ASSIGN(Scanning);
};

}  // namespace shim
}  // namespace bluetooth
