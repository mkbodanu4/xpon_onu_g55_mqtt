# MQTT Client for XPON ONU G55
Service to send status and alarms from XPON ONU G55 to Home Assistant using MQTT

### Installation

Install dependencies using `pip`:

```sh
$ pip install paho-mqtt
```

### Configuration

Open `configuration.yaml` and update IP address of XPON ONU G55, username, login and MQTT auth data.

### Running with CLI:

```sh
$ python mqtt.py
```

## Running as service (via systemd)

1. Copy `g55.service` to systemd configuration folder

```sh
$ sudo cp ./g55.service /etc/systemd/system/ 
```

2. Open file with text editor

```sh
$ sudo nano /etc/systemd/system/g55.service
```

3. If Mosquitto service running on another server, remove `mosquitto.service` from `After` option of `[Unit]` section.

4. Update `WorkingDirectory` and `ExecStart` with proper path to code.

5. Start and enable service

```sh
$ sudo systemctl start g55
$ sudo systemctl enable g55
```

# Licence

Code is licensed under the terms of the MIT License (see the file LICENSE).
