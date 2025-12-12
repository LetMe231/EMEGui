import ephem
from datetime import timezone, datetime

# Observer position
observer = ephem.Observer()
observer.lat = '47.2237270'              # Latitude
observer.lon = ' 8.8176838'              # Longitude
observer.elev = 466.63                   # Elevation in meters

def get_moon_position():
    """
    Calculate Position of the Moon in the Sky with respect of the current Location.

    returns: az - Azimuth and el - Elevation of the Moon.
    """
    # Make sure we update the time each call
    observer.date = ephem.now()
    moon = ephem.Moon(observer)
    az = float(moon.az) * 180.0 / ephem.pi
    el = float(moon.alt) * 180.0 / ephem.pi
    return az, el

def get_moon_threshold_times(min_el_deg=15.0):
    """
    Return next times (UTC) when the Moon crosses the given elevation:

      - next_above: next time Moon goes ABOVE min_el_deg (rising through it)
      - next_below: next time Moon goes BELOW min_el_deg (setting through it)

    Returned as ISO strings in UTC (for JS).
    """
    obs = observer
    obs.date = ephem.now()
    obs.horizon = f"{min_el_deg:.2f}"

    moon = ephem.Moon()
    moon.compute(obs)

    # These return ephem.Date (UTC)
    next_rise   = obs.next_rising(moon)
    next_set    = obs.next_setting(moon)

    # Convert to Python datetimes in UTC, then ISO
    def to_iso(d):
        dt = d.datetime()
        # mark as UTC explicitly
        return dt.replace(tzinfo=timezone.utc).isoformat()

    return to_iso(next_rise), to_iso(next_set)

def get_observer():
    return observer
