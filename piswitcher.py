import serial
import time
from gpiozero import Button
from signal import pause
import logging
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)


class Relay(object):
    logger = logging.getLogger('Relay')

    BAUDRATE = 9600
    COMMANDS = {
        (False, False): 0,
        (False, True): 1,
        (True, False): 2,
        (True, True): 3
    }

    POWERUP = ['\x50', '\x51']

    def __init__(self, serial_port):
        self._port = serial.Serial(serial_port, baudrate=self.BAUDRATE)

        self.logger.info('Initializing relay board')

        self._port.write('\x50')
        time.sleep(1)
        result = self._port.read_all()
        if result and ord(result) == 0xAD:
            self._port.write('\x51')
            time.sleep(1)

        self.notifier = None

        self.logger.info('Resetting state')
        self._relays = [False] * 2
        self._update_relay()

    def _update_relay(self):
        state = self.COMMANDS[(self._relays[0], self._relays[1])]
        return self._port.write(bytearray([state]))

    def _notify_change(self, switch, state):
        action = {False: 'OFF', True: 'ON'}[state]
        self.logger.info("Switch %d was set to '%s'", switch, action)
        if self.notifier:
            self.notifier(int(switch), action)

    def refresh_state(self):
        if not self.notifier:
            logger.warn("No notifier found, refresh will not happen")
            return False

        for i, state in enumerate(self._relays):
            self._notify_change(i, state)
            time.sleep(1)

        return True

    def all_off(self):
        self._relays = [False] * 2
        self._update_relay()
        self.refresh_state()

    def all_on(self):
        self._relays = [True] * 2
        self._update_relay()
        self.refresh_state()
        return self._update_relay()

    def set(self, switch, state=False):
        if self._relays[switch] == state:
            self.logger.info("Switch %d state didn't change", switch)

        self._relays[switch] = state
        result = self._update_relay()
        if result == 1:
            self._notify_change(switch, state)

        return result

    def get(self, switch):
        return self._relays[switch]

    def toggle(self, switch):
        return self.set(switch, not self.get(switch))

    def toggle_one(self):
        return self.toggle(0)

    def toggle_two(self):
        return self.toggle(1)


class RelayHandler(object):
    logger = logging.getLogger('RelayHandler')

    STATUS_TOPIC = '{command}/relayarray0/relay{relay_number}'
    STATUS_TOPIC_ALL = 'cmnd/relayarray0'

    def __init__(self, relay, mqtt_hostname, mqtt_port=1883):
        self._mqtt_port = mqtt_port
        self._mqtt_hostname = mqtt_hostname
        self.client = mqtt.Client('RelayArray-ID1')
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

        client.subscribe([(switch_one, 0), (switch_two, 0)])
        client.message_callback_add(switch_one,
                                    lambda client, userdata, message: self._handle_relay_command(0, message))
        client.message_callback_add(switch_two,
                                    lambda client, userdata, message: self._handle_relay_command(1, message))
        client.message_callback_add(self.STATUS_TOPIC_ALL,
                                    lambda client, userdata, message: self._handle_relay_command_all(message))

        self._relay.all_off()

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
        self.logger.info('Recieved message: %s', msg.payload)

    def notifier(self, relay_number, action):
        #import pdb; pdb.set_trace()
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


def run():
    relay_device = '/dev/ttyAMA0' # 'COM6'
    ha_host = '192.168.14.192'

    logger.info('Starting service')
    relay = Relay(relay_device)
    relay_handler = RelayHandler(relay, ha_host)

#    while True:
#        time.sleep(0.5)
    
    b_1 = Button(18)
    b_2 = Button(17)

    b_1.when_pressed = relay.toggle_one
    b_1.when_released = relay.toggle_one
    
    b_2.when_pressed = relay.toggle_two
    b_2.when_released = relay.toggle_two

    pause()


if __name__ == "__main__":
    run()
