import argparse
import time

from piswitcher.relay import Relay
from piswitcher.relay_handler import RelayHandler

ON_DEVICE = True
try:
    from gpiozero import Button
    from signal import pause
except Exception as e:
    ON_DEVICE = False

import logging

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)


def get_opts():
    parser = argparse.ArgumentParser(prog='Pi Switcher', description='Relay handler daemon for ICSE01xA',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--relay_device', type=str, default='/dev/ttyAMA0')
    parser.add_argument('--ha_host', type=str, default='192.168.14.192', help='Address of HA MQTT server')
    parser.add_argument('--button_one_gpio', type=int, default=17,
                        help='GPIO Pin to handle as physical switch for relay 1')
    parser.add_argument('--button_two_gpio', type=int, default=18,
                        help='GPIO Pin to handle as physical switch for relay 2')

    return parser.parse_args()


def run():
    args = get_opts()

    b1_gpio = args.button_one_gpio
    b2_gpio = args.button_two_gpio

    ha_host = args.ha_host
    relay_device = args.relay_device

    logger.info('Starting service')
    relay = Relay(relay_device)
    relay_handler = RelayHandler(relay, ha_host)

    if ON_DEVICE:
        b_1 = Button(b1_gpio)
        b_2 = Button(b2_gpio)

        b_1.when_pressed = relay.toggle_one
        b_1.when_released = relay.toggle_one

        b_2.when_pressed = relay.toggle_two
        b_2.when_released = relay.toggle_two

        pause()
    else:
        while True:
            time.sleep(0.5)


if __name__ == "__main__":
    run()
