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

### HACS custom repository

1. Open HACS.
2. Open **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add this repository URL:

```text
https://github.com/TheBam1990/homeassistant-advansol-optimizer-0.1.0
```

5. Select category **Integration**.
6. Install **AdvanSol Optimizer** and restart Home Assistant.

If HACS reports **401 Unauthorized**, Home Assistant cannot authenticate against the GitHub API. The repository is public, so this normally means the HACS GitHub token/session is invalid or rate-limited. Re-authenticate HACS with GitHub or add a valid GitHub token in HACS, then retry.

### Manual installation

Copy the folder:

```text
custom_components/advansol_optimizer
```

to your Home Assistant configuration directory:

```text
/config/custom_components/advansol_optimizer
```

Then restart Home Assistant.

### Direct installation from GitHub on a Docker host

The following example downloads the current `main` branch directly from GitHub. Run the commands on the Docker host as `root` (or prefix the Docker and file commands with `sudo`):

```bash
curl -fsSL \
  https://github.com/TheBam1990/homeassistant-advansol-optimizer-0.1.0/archive/refs/heads/main.tar.gz \
  -o /tmp/advansol-main.tar.gz
tar -xzf /tmp/advansol-main.tar.gz -C /tmp
mkdir -p /homeassistant/config/custom_components
cp -a \
  /tmp/homeassistant-advansol-optimizer-0.1.0-main/custom_components/advansol_optimizer \
  /homeassistant/config/custom_components/
docker exec homeassistant python3 -m homeassistant --script check_config -c /config
docker restart homeassistant
```

In this example, the Home Assistant container is named `homeassistant` and the host directory `/homeassistant/config` is mounted as `/config`. Check and adjust both values for your installation:

```bash
docker ps --format '{{.Names}}'
docker inspect homeassistant --format '{{json .Mounts}}'
```

After the restart, open **Settings** -> **Devices & services** -> **Add integration** and search for **AdvanSol Optimizer**.

## Setup

In Home Assistant:

1. Go to **Settings** -> **Devices & services**.
2. Click **Add integration**.
3. Search for **AdvanSol Optimizer**.
4. Enter the TCP bridge settings.

Default values:

- Host: `192.0.2.1` (documentation example; replace it with your bridge address)
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

By default, the first setup validates the connection by reading the controller serial number. If the optimizers do not answer during the configured night period or there is no PV-side supply, enable **Skip connection test during setup**. The integration will then load as disconnected and poll again later.

The integration creates entities for modules found during startup. If modules are added or removed later, reload the integration or restart Home Assistant.
