import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from sgp4.earth_gravity import wgs84
from skyfield.api import load, Topos, EarthSatellite, wgs84
import numpy as np
from datetime import timedelta, datetime


def create_horizon_grid(observer_lat, observer_lon, cell_size=1.0, horizon_radius=5.0):
    """
        Creates a grid representing the area around an observer.

        The function generates a set of latitude and longitude coordinates based on an observer's position,
        within a defined radius, and divides that area into cells of a specified size. Each cell is represented
        by a pair of coordinates and can store a list of visible satellites.

        Args:
            observer_lat (float): The latitude of the observer's position.
            observer_lon (float): The longitude of the observer's position.
            cell_size (float): The size of the grid cells in degrees, defining the resolution of the grid (default is 2.0).
            horizon_radius (float): The radius in degrees of the area around the observer to be covered by the grid (default is 10.0).

        Returns:
            np.array: An array of dictionaries, where each dictionary contains:
                - 'latitude': The latitude of the cell.
                - 'longitude': The longitude of the cell.
                - 'satellites': An empty list to store satellites visible in the cell.
    """
    # Creates arrays of latitude and longitude values around the observer based on the cell size and horizon radius
    lat_range = np.arange(observer_lat - horizon_radius, observer_lat + horizon_radius, cell_size)
    lon_range = np.arange(observer_lon - horizon_radius, observer_lon + horizon_radius, cell_size)

    grid = np.array([{"latitude": lat, "longitude": lon, "satellites": []} for lat in lat_range for lon in lon_range])

    return grid

def calculate_visible_satellites(observer_lat, observer_lon, satellites, start_time, end_time, interval, cell_size=1.0,
                                 horizon_radius=10.0):
    """
        Calculates the visible satellites for each cell in a grid over a given time period.

        This function determines which satellites are visible from the observer's location, within a defined
        horizon radius, over a specified time range. It updates a grid of cells, marking each cell with the
        satellites visible from that location during the given times.

        Args:
            observer_lat (float): The latitude of the observer's position.
            observer_lon (float): The longitude of the observer's position.
            satellites (list): A list of satellite objects to check for visibility.
            start_time (datetime): The starting time of the observation period.
            end_time (datetime): The ending time of the observation period.
            interval (timedelta): The time interval between each visibility check.
            cell_size (float): The size of the grid cells in degrees (default is 1.0).
            horizon_radius (float): The radius in degrees of the area around the observer to be checked (default is 10.0).

        Returns:
            np.array: A grid where each cell contains information about visible satellites:
                - 'satellite': The name of the satellite.
                - 'time': The time when the satellite was visible.
                - 'altitude': The altitude of the satellite above the horizon.
                - 'azimuth': The azimuth angle of the satellite.
    """
    ts = load.timescale()
    grid = create_horizon_grid(observer_lat, observer_lon, cell_size, horizon_radius)

    current_time = start_time

    while current_time <= end_time:
        t = ts.utc(current_time.year, current_time.month, current_time.day, current_time.hour, current_time.minute,
                   current_time.second)
        observer = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon)
        # Check each satellite for visibility
        for satellite in satellites:
            difference = satellite - observer
            topocentric = difference.at(t)
            alt, az, distance = topocentric.altaz()

            # Calculate the satellite's latitude and longitude
            geocentric = satellite.at(t)
            sat_lat, sat_lon = wgs84.latlon_of(geocentric)
            # If the satellite is above the horizon (altitude > 0 degrees)
            if alt.degrees > 0:
                for cell in grid:
                    cell_lat = cell["latitude"]
                    cell_lon = cell["longitude"]

                    # Check if the satellite is within the bounds of the current grid cell
                    if (cell_lat <= sat_lat.degrees < cell_lat + cell_size) and (cell_lon <= sat_lon.degrees < cell_lon + cell_size):
                        # Update the cell with satellite data and the corresponding time
                        cell["satellites"].append({
                            "satellite": satellite.name,
                            "time": current_time,
                            "altitude": alt.degrees,
                            "azimuth": az.degrees
                        })

        # Advance time by the specified interval
        current_time += interval

    return grid