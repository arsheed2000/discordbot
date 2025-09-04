import discord
import johnnydep
from FlightRadar24 import FlightRadar24API
from FlightRadar24 import Countries
from haversine import haversine
import math
from PIL import Image
import io


def is_flight_in_circle(flight_lat, flight_lon, CENTER_LAT, CENTER_LON, RADIUS_KM):
    """
    Check if a flight is within the specified circular area.
    """
    distance = haversine((flight_lat, flight_lon), (CENTER_LAT, CENTER_LON))
    return distance <= RADIUS_KM


class Flight:

    fr_api = FlightRadar24API()
    fr_apic = Countries
    #flights = fr_api.get_flights()

    LAT, LON = 50.168123164443145, 8.976226273312639
    RADIUS_M = 30000

    bounds = fr_api.get_bounds_by_point(LAT, LON, RADIUS_M)
    flights = fr_api.get_flights(bounds=bounds)
    details = fr_api.get_flight_details(flights[0])
    flight = flights[0]
    flight.set_flight_details(details)
    airport = fr_api.get_airport("FRA")
    flight_pos = (flight.latitude, flight.longitude)

    distance = haversine(flight_pos,(LAT, LON))


    lat = flight.latitude
    lon = flight.longitude
    cord = (lat, lon)

    rand = flight.aircraft_country_id

    yes = is_flight_in_circle(lat, lon, LAT, LON, 10)
    print(len(flights))
    for i in flights:

        if is_flight_in_circle(i.latitude, i.longitude, LAT, LON, 10):
            print(f'The following flight is in Radius: {i}')

    print(yes)



    print(" ")
    print(f'keys: {details.keys()}')
    print(details["status"])

"""
    print(f'top keys: {data.keys()}')
    print(" ")
    print(f'keys of airport: {data["airport"].keys()}')
    print(" ")
    print(f'keys of pluginData: {data["airport"]["pluginData"].keys()}')
    print(" ")
    print(data["airport"]["pluginData"]["details"].keys())
    print(" ")
    print(data["airport"]["pluginData"]["details"])
"""



