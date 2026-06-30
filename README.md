# Home Assistant AdvanSol Optimizer Integration

Custom integration for AdvanSol DCON-WIFI / MRO/MR optimizers connected through a TCP RS485 bridge.

This project is a Home Assistant port of the ioBroker adapter `iobroker.advansol-optimizer`. It uses the same TCP frame protocol, CRC handling, controller discovery and module value decoding.

## Features

- Connects directly to the TCP RS485 bridge.
- Reads the AdvanSol controller serial number.
- Discovers optimizer modules.
- Creates Home Assistant devices for controller and optimizers.
- Polls optimizer values:
  - serial number
  - MOS status
  - software and hardware version
  - output voltage/current
  - input voltage/current
  - temperature
  - power
  - total energy
  - raw response
- Provides one MOS switch per optimizer module.
- Supports a configurable night window where polling is skipped.

## Installation

Copy the folder:

```text
custom_components/advansol_optimizer
```

to your Home Assistant configuration directory:

```text
/config/custom_components/advansol_optimizer
```

Then restart Home Assistant.

## Setup

In Home Assistant:

1. Go to **Settings** -> **Devices & services**.
2. Click **Add integration**.
3. Search for **AdvanSol Optimizer**.
4. Enter the TCP bridge settings.

Default values:

- Host: `192.168.2.156`
- TCP port: `502`
- Poll interval: `10` seconds
- Request timeout: `5` seconds
- Switch retries: `3`
- Switch retry delay: `4.1` seconds
- Night start: `22`
- Night end: `5`

## Entities

Controller:

- `binary_sensor.*_connection`
- `binary_sensor.*_night_mode`
- `sensor.*_controller_serial_number`
- `sensor.*_module_count`

Per optimizer module:

- `switch.*_mos`
- `sensor.*_output_voltage`
- `sensor.*_output_current`
- `sensor.*_power`
- `sensor.*_total_energy`
- `sensor.*_input_voltage`
- `sensor.*_input_current`
- `sensor.*_temperature`
- `sensor.*_mos_status`
- `sensor.*_software_version`
- `sensor.*_hardware_version`
- `sensor.*_serial_number`
- `sensor.*_raw_response`

## Notes

The first setup validates the connection by reading the controller serial number. If the optimizers do not answer during the configured night period or there is no PV-side supply, setup can fail. In that case retry when the controller and modules are powered and reachable.

The integration creates entities for modules found during startup. If modules are added or removed later, reload the integration or restart Home Assistant.
