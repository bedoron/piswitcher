import logging
import time

import serial


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
        if result and ord(result) in [0xAD, 0xAB, 0xAC]:
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
            self.logger.warn("No notifier found, refresh will not happen")
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
            self.logger.debug("Switch %d state didn't change", switch)

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
