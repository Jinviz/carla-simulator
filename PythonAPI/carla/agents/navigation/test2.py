
import carla

from carla import ColorConverter as cc

import argparse
import collections
import datetime
import logging
import math
import random
import re
import weakref

try:
    import pygame
    from pygame.locals import KMOD_CTRL
    from pygame.locals import KMOD_SHIFT
    from pygame.locals import K_0
    from pygame.locals import K_9
    from pygame.locals import K_BACKQUOTE
    from pygame.locals import K_BACKSPACE
    from pygame.locals import K_COMMA
    from pygame.locals import K_DOWN
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_F1
    from pygame.locals import K_LEFT
    from pygame.locals import K_PERIOD
    from pygame.locals import K_RIGHT
    from pygame.locals import K_SLASH
    from pygame.locals import K_SPACE
    from pygame.locals import K_TAB
    from pygame.locals import K_UP
    from pygame.locals import K_a
    from pygame.locals import K_b
    from pygame.locals import K_c
    from pygame.locals import K_d
    from pygame.locals import K_f
    from pygame.locals import K_g
    from pygame.locals import K_h
    from pygame.locals import K_i
    from pygame.locals import K_l
    from pygame.locals import K_m
    from pygame.locals import K_n
    from pygame.locals import K_o
    from pygame.locals import K_p
    from pygame.locals import K_q
    from pygame.locals import K_r
    from pygame.locals import K_s
    from pygame.locals import K_t
    from pygame.locals import K_v
    from pygame.locals import K_w
    from pygame.locals import K_x
    from pygame.locals import K_z
    from pygame.locals import K_MINUS
    from pygame.locals import K_EQUALS
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')

try:
    import numpy as np
except ImportError:
    raise RuntimeError('cannot import numpy, make sure numpy package is installed')

import basic_agent


def set_destination_manual(agent):
    while True:
        try:
            end_x = float(input("Enter X coordinate of the destination: "))
            end_y = float(input("Enter Y coordinate of the destination: "))
            end_z = float(input("Enter Z coordinate of the destination: "))
            end_location = carla.Location(x=end_x, y=end_y, z=end_z)
            agent.set_destination(end_location)
            print("Destination set successfully.")
            break
        except ValueError:
            print("Invalid input. Please enter numerical values.")


def game_loop(args):
    pygame.init()
    pygame.font.init()

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(2000.0)

        world = client.get_world()
        map = world.get_map()

        display = pygame.display.set_mode((args.width, args.height), pygame.HWSURFACE | pygame.DOUBLEBUF)
        display.fill((0, 0, 0))
        pygame.display.flip()

        # Create a vehicle at a specific spawn point
        spawn_point = carla.Transform(carla.Location(x=285, y=-66, z=0.5), carla.Rotation(yaw=0))
        vehicle = world.spawn_actor(world.get_blueprint_library().find('vehicle.tesla.model3'), spawn_point)

        # Create a basic agent to control the vehicle
        agent = basic_agent.BasicAgent(vehicle)

        clock = pygame.time.Clock()
        is_auto_pilot = False

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                # Toggle auto_pilot mode when 'P' key is pressed
                if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                    if is_auto_pilot:
                        agent.ignore_traffic_lights(False)
                        is_auto_pilot = False
                        print("Auto-pilot mode OFF")
                    else:
                        agent.ignore_traffic_lights(True)
                        is_auto_pilot = True
                        print("Auto-pilot mode ON")

                    # If auto_pilot is on, set the destination automatically
                    if is_auto_pilot:
                        set_destination_manual(agent)

            control = pygame.key.get_pressed()

            if control[pygame.K_w]:
                agent.set_target_speed(20)  # Set target speed to 20 Km/h
            elif control[pygame.K_s]:
                agent.set_target_speed(0)  # Set target speed to 0 Km/h
            else:
                agent.set_target_speed(10)  # Set target speed to 10 Km/h (default)

            if control[pygame.K_a]:
                agent.lane_change('left')  # Perform left lane change
            elif control[pygame.K_d]:
                agent.lane_change('right')  # Perform right lane change

            if not is_auto_pilot:
                control = agent.run_step()
                vehicle.apply_control(control)

            clock.tick_busy_loop(60)
            world.tick()
            world.render(display)
            pygame.display.flip()

    finally:
        vehicle.destroy()
        pygame.quit()


def main():
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='window resolution (default: 1280x720)')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.*',
        help='actor filter (default: "vehicle.*")')
    argparser.add_argument(
        '--generation',
        metavar='G',
        default='2',
        help='restrict to certain actor generation (values: "1","2","All" - default: "2")')
    argparser.add_argument(
        '--rolename',
        metavar='NAME',
        default='hero',
        help='actor role name (default: "hero")')
    argparser.add_argument(
        '--gamma',
        default=2.2,
        type=float,
        help='Gamma correction of the camera (default: 2.2)')
    argparser.add_argument(
        '--sync',
        action='store_true',
        help='Activate synchronous mode execution')
    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.info('listening to server %s:%s', args.host, args.port)

    print(__doc__)

    try:

        game_loop(args)

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')
print("1111111111111111111111")

if __name__ == '__main__':

    main()

