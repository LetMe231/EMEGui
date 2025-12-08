import ephem

# Observer position

observer = ephem.Observer()
observer.lat = '47.2237270'              # Latitude
observer.lon = ' 8.8176838'              # Longitude
observer.elev = 466.63                   # Elevation in meters
observer.date = ephem.now()

def get_moon_position():
    """
    Calculate Position of the Moon in the Sky with respect of the current Location.

    returns: az - Azimuth and el - Elevation of the Moon.
    """
    moon = ephem.Moon(observer)
    az = float(moon.az) * 180.0 / ephem.pi
    el = float(moon.alt) * 180.0 / ephem.pi
    return az, el

def get_observer():
    return observer