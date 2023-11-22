import glob
import os
import sys
import argparse
import math


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(value, maximum))


class Sun(object):
    def __init__(self, sun_azimuth_angle, sun_altitude_angle):
        self.azimuth = sun_azimuth_angle
        self.altitude = sun_altitude_angle
        self._t = 0.0

    def tick(self, delta_seconds, sun_set):
        if sun_set[2] is True:
            self._t += 0.008 * delta_seconds
            self._t %= 2.0 * math.pi
            self.azimuth += 0.25 * delta_seconds
            self.azimuth %= 360.0
            self.altitude = (70 * math.sin(self._t)) - 20
        elif sun_set[2] is False:
            self.azimuth = sun_set[0]
            self.altitude = sun_set[1]

    def __str__(self):
        return 'Sun(alt: %.2f, azm: %.2f)' % (self.altitude, self.azimuth)


class Storm(object):
    def __init__(self, precipitation):
        self._t = precipitation if precipitation > 0.0 else -50.0
        self._increasing = True
        self.clouds = 0.0
        self.rain = 0.0
        self.wetness = 0.0
        self.puddles = 0.0
        self.wind = 0.0
        self.fog = 0.0
        self.remote = False

    def tick(self, delta_seconds, weather_set):
        """
        :param delta_seconds: timestamp = world.wait_for_tick().timestamp
        :param weather_set: weather_set = [clouds, rain, wetness, puddles, wind, fog, remote]
        remote가  True인 경우 동적모드 활성화
        """

        self.remote = weather_set[6]
        if self.remote:
            delta = (1.3 if self._increasing else -1.3) * delta_seconds
            self._t = clamp(delta + self._t, -250.0, 100.0)
            self.clouds = clamp(self._t + 40.0, 0.0, 90.0)
            self.rain = clamp(self._t, 0.0, 80.0)
            delay = -10.0 if self._increasing else 90.0
            self.puddles = clamp(self._t + delay, 0.0, 85.0)
            self.wetness = clamp(self._t * 5, 0.0, 100.0)

            if self._t == -250.0:
                self._increasing = True
            if self._t == 100.0:
                self._increasing = False
        else:
            self.clouds = weather_set[0]
            self.rain = weather_set[1]
            self.wetness = weather_set[2]
            self.puddles = weather_set[3]
            self.wind = weather_set[4]
            self.fog = weather_set[5]

    def __str__(self):
        return 'Rain(rain=%d%%, wetness=%d%%, puddles=%d%%)' % (self.rain, self.wetness, self.puddles)


class Weather(object):
    def __init__(self, weather, world):
        self.weather = weather
        self.world = world
        self._sun = Sun(weather.sun_azimuth_angle, weather.sun_altitude_angle)
        self._storm = Storm(weather.precipitation)

    def tick(self, delta_seconds, weather_set, sun_set):
        self._sun.tick(delta_seconds, sun_set)
        self._storm.tick(delta_seconds, weather_set)

        self.weather.precipitation = self._storm.rain
        self.weather.precipitation_deposits = self._storm.puddles
        self.weather.wetness = self._storm.wetness
        self.weather.cloudiness = self._storm.clouds
        self.weather.fog_density = self._storm.fog
        self.weather.wind_intensity = self._storm.wind

        self.weather.sun_azimuth_angle = self._sun.azimuth
        self.weather.sun_altitude_angle = self._sun.altitude

        # carla update
        self.world.set_weather(self.weather)
