import ephem

# Moon position
def get_moon_position():
    """
    Calculate Position of the Moon in the Sky with respect of the current Location.

    returns: az - Azimuth and el - Elevation of the Moon.
    """
    observer = ephem.Observer()
    observer.lat = '47.22373165068804'    # Latitude
    observer.lon = '8.817665635178574'    # Longitude
    observer.elev = 451                   # Elevation in meters
    observer.date = ephem.now()
    moon = ephem.Moon(observer)
    az = float(moon.az) * 180.0 / ephem.pi
    el = float(moon.alt) * 180.0 / ephem.pi
    return az, el

