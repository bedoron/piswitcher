import logging

from paho.mqtt import client as mqtt
import random


class RelayHandler(object):
    logger = logging.getLogger('RelayHandler')

    STATUS_TOPIC = '{command}/relayarray0/relay{relay_number}'
    STATUS_TOPIC_ALL = 'cmnd/relayarray0'

    def __init__(self, relay, mqtt_hostname, mqtt_port=1883):
        self._mqtt_port = mqtt_port
        self._mqtt_hostname = mqtt_hostname
        self.client = mqtt.Client('RelayArray-ID{}'.format(random.randint(10, 99)))
        self._relay = relay
        self._relay.notifier = self.notifier
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._timestamps = [0] * 2

        self.client.connect(self._mqtt_hostname, self._mqtt_port)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        # import pdb; pdb.set_trace()
        self.logger.info('Connected to HA MQTT')
        switch_one = self.STATUS_TOPIC.format(command='cmnd', relay_number=0)
        switch_two = self.STATUS_TOPIC.format(command='cmnd', relay_number=1)

        client.subscribe([(switch_one, 0), (switch_two, 0), (self.STATUS_TOPIC_ALL, 0)])
        client.message_callback_add(switch_one,
                                    lambda client, userdata, message: self._handle_relay_command(0, message))
        client.message_callback_add(switch_two,
                                    lambda client, userdata, message: self._handle_relay_command(1, message))
        client.message_callback_add(self.STATUS_TOPIC_ALL,
                                    lambda client, userdata, message: self._handle_relay_command_all(message))

        self._relay.all_off()

    def _on_log(self, client, userdata, level, buf):
        self.logger.info('[%s] %s', level, buf)

    def _handle_relay_command(self, switch, payload):
        # self.logger.debug('Recieved MQTT message: %s', json.dumps(payload))

        action = payload.payload
        timestamp = payload.timestamp
        if timestamp < self._timestamps[switch]:
            self.logger.warn('Ignoring relay %d command "%s" as its ts %d is older than %d', switch, action, timestamp,
                             self._timestamps[switch])

        self._timestamps[switch] = timestamp
        self.logger.info('Handling relay %d command "%s"', switch, action)
        action = action.upper() if action else action
        resolved_action = {'ON': True, 'OFF': False}.get(action, False)
        self._relay.set(switch, resolved_action)

    def _on_message(self, client, userdata, msg):
        self.logger.info('Received message: %s', msg.payload)

    def notifier(self, relay_number, action):
        # import pdb; pdb.set_trace()
        topic = self.STATUS_TOPIC.format(command='stat', relay_number=relay_number)
        result = self.client.publish(topic, action)

    def _handle_relay_command_all(self, payload):
        self._timestamps = [0] * 2  # TODO: Fix this
        action = payload.message
        action = action.higher() if action else action
        if action == 'ON':
            self._relay.all_on()
        elif action == 'OFF':
            self._relay.all_off()
