from gpiozero import DigitalInputDevice
from vcgencmd import Vcgencmd

from threading import Timer, Event
import os
import json


with open('pwrmgr.json', 'r') as r:
    config = json.load(r)

IGNITION_PIN = config['ignition_pin']
POWERBUTTON_PIN = config['powerbutton_pin']
CAMERA_PIN = config['camera_pin']
POWEROFF_TIME = config['poweroff_time']
SCREENOFF_TIME = config['screenoff_time']
POWERBUTTON_HOLD_TIME = config['powerbutton_hold_time']
DISP_ID = config['disp_id']

vcgm = Vcgencmd()

poweroff_timer: Timer = None
screenoff_timer: Timer = None
buttonhold_timer: Timer = None

ignition = DigitalInputDevice(
    IGNITION_PIN, pull_up=False, bounce_time=0.05)
powerbutton = DigitalInputDevice(POWERBUTTON_PIN,  pull_up=True,
                                 bounce_time=0.01,
                                 )
camera = DigitalInputDevice(CAMERA_PIN, pull_up=False, bounce_time=0.01)


def system_poweroff():
    os.system("sudo poweroff")


def screenoff():
    if ignition.value or camera.value:
        print('not turning screen off because ignition or camera is still on')
        return
    print('turning screen off')
    vcgm.display_power_off(DISP_ID)


def screenon():
    print('turning screen on')
    vcgm.display_power_on(DISP_ID)


def screenstate():
    return vcgm.display_power_state(DISP_ID)


def schedule_screenoff():
    global screenoff_timer
    screenoff_timer = Timer(SCREENOFF_TIME, screenoff)
    screenoff_timer.start()


def cancel_screenoff():
    global screenoff_timer
    if screenoff_timer:
        screenoff_timer.cancel()
        screenoff_timer = None


def on_ignition_on():
    print('ignition on')

    global poweroff_timer

    if poweroff_timer:
        poweroff_timer.cancel()
        poweroff_timer = None
    cancel_screenoff()
    if screenstate() == 'off':
        screenon()


def on_ignition_off():
    print('ignition off, powering off in {} seconds'.format(POWEROFF_TIME))

    global poweroff_timer

    poweroff_timer = Timer(POWEROFF_TIME, system_poweroff)
    poweroff_timer.start()
    schedule_screenoff()


def on_powerbutton_release():
    global buttonhold_timer
    print('power button clicked')

    # if button is released before timer has finished
    if buttonhold_timer:
        print('cancelling button poweroff')
        buttonhold_timer.cancel()
        buttonhold_timer = None

    screenon() if screenstate() == 'off' else screenoff()


def on_powerbutton_press():
    global buttonhold_timer
    buttonhold_timer = Timer(POWERBUTTON_HOLD_TIME, on_powerbutton_held)
    buttonhold_timer.start()


def on_powerbutton_held():
    global buttonhold_timer
    print('powerbutton held')
    buttonhold_timer = None
    system_poweroff()


was_screen_off = False


def on_camera_on():
    global was_screen_off

    cancel_screenoff()
    if screenstate() == 'off':
        screenon()
        was_screen_off = True


def on_camera_off():
    if was_screen_off:
        schedule_screenoff()


def main():

    if ignition.value == 0:
        on_ignition_off()

    ignition.when_activated = on_ignition_on
    ignition.when_deactivated = on_ignition_off
    powerbutton.when_activated = on_powerbutton_press
    powerbutton.when_deactivated = on_powerbutton_release
    camera.when_activated = on_camera_on
    camera.when_deactivated = on_camera_off

    event = Event()
    while True:
        event.wait()


if __name__ == "__main__":
    main()
