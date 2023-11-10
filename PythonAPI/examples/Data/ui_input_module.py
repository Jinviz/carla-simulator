def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(value, maximum))

class UI_INPUT_CONTROL(object):
    def return_sun_type(self, sun_type="midday", remote=False):
        azimuth = 0
        altitude = 0
        if remote is False:  # 수동
            if sun_type == "midday":
                azimuth = 230
                altitude = 90
            elif sun_type == "sunset":
                azimuth = 330  # 0 - 180
                altitude = 10  # 90 ~ -90
            elif sun_type == "midnight":
                azimuth = 60
                altitude = -30

        sun_set = [azimuth, altitude, remote]
        return sun_set

    def return_weather(self, clouds=0.0, rain=0.0, wetness=0.0, puddles=0.0, wind=0.0, fog=0.0, remote=False):
        clouds = clamp(clouds, 0.0, 100.0)
        rain = clamp(rain, 0.0, 100.0)
        wetness = clamp(wetness, 0.0, 100.0)
        puddles = clamp(puddles, 0.0, 100.0)
        wind = clamp(wind, 0.0, 100.0)
        fog = clamp(fog, 0.0, 100.0)
        remote = remote
        weather_set = [clouds, rain, wetness, puddles, wind, fog, remote]
        return weather_set
