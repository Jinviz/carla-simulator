
from __future__ import print_function


# ==============================================================================
# -- find carla module ---------------------------------------------------------
# ==============================================================================


import glob
import os
import sys

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


# ==============================================================================
# -- imports -------------------------------------------------------------------
# ==============================================================================

import basic_agent
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
        spawn_point = carla.Transform(carla.Location(x=9036.62207, y=-19716.265625, z=0.0), carla.Rotation(yaw=0))
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
                            end_location = carla.Location(x=16430.222656, y=-19716.265625,
                                                          z=0.0)  # Change this to your desired destination
                            agent.set_destination(end_location)

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

            if is_auto_pilot:
                agent.run_step()

            vehicle.apply_control(control)

            clock.tick_busy_loop(60)
            world.tick()
            world.render(display)
            pygame.display.flip()

    finally:
        vehicle.destroy()
        pygame.quit()


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.host = "localhost"
    args.port = 2000
    args.width = 800
    args.height = 600
    game_loop(args)
