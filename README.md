Control ICSE013A Using raspberry pi with mqtt integration in order to work with Home assistant,
The device supports using physical switches in order to integrate it with wall switches.

Home assistant usage example:
```yaml
switch:
  - platform: mqtt
    name: "Relay 1"
    state_topic: "stat/relayarray0/relay0"
    command_topic: "cmnd/relayarray0/relay0"
    qos: 0
    payload_on: "ON"
    payload_off: "OFF"
    optimistic: false
    retain: true
  - platform: mqtt
    name: "Relay 2"
    state_topic: "stat/relayarray0/relay1"
    command_topic: "cmnd/relayarray0/relay1"
    qos: 0
    payload_on: "ON"
    payload_off: "OFF"
    optimistic: false
    retain: true
```

Device also support control to both sockets together on subject `{action}/relayarray0` but I've never tested it.

Notice that:
# stat is used in order to communicate the switches back to HA
# cmnd is used to accept command from HA

