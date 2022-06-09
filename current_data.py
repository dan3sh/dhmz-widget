"""Get all current weather measurements in one place and render a html page."""
from dataclasses import dataclass
from os import path
from xml.etree.ElementTree import fromstring

from jinja2 import Environment, FileSystemLoader
from requests import get
from xmljson import parker as pk

GENERAL_WEATHER_SOURCE = "https://vrijeme.hr/hrvatska_n.xml"
UVI_SOURCE = "https://vrijeme.hr/uvi.xml"
SEA_TEMPERATURE_SOURCE = "https://vrijeme.hr/more_n.xml"


@dataclass
class Station:
    """Base class containing station measurements."""

    name: str
    measurements: dict


def find_current_reading(points):
    """Return current (last) time and reading data."""

    for time, reading in reversed(points.items()):
        if not reading:
            continue
        return time, reading


def get_data_from(source):
    """Get XML data from a given data source."""

    datapoints = get(source)
    xml = str(datapoints.content.decode("utf-8"))
    raw_data = pk.data(fromstring(xml))

    return raw_data


def extract_stations_from(raw_data):
    """Return a dict of Stations for any type of data source."""

    weather_stations = {}

    data = raw_data.get("Grad")
    if data:
        [
            weather_stations.update(
                {
                    i.get("GradIme"): Station(name=i.get("GradIme"), measurements=i.get("Podatci"))
                }
            )
            for i in data
        ]

    else:
        measurement_keys = raw_data.get("Podatci")[0].get("Termin")
        data = raw_data.get("Podatci")[1:]

        for i in data:
            measurements = dict(
                {measurement_keys[x]: i.get("Termin")[x] for x in range(len(i.get("Termin")))}
            )
            name = i.get("Postaja")
            weather_stations.update({name: Station(name=name,measurements=measurements)})

    return weather_stations


def get_current_uv_reading(station_name):
    raw_data = get_data_from(UVI_SOURCE)

    weather_stations = extract_stations_from(raw_data)
    station = weather_stations.get(station_name)

    if not station:
        return (f"Podaci za stanicu {station_name} nisu dostupni.", "-")
    return find_current_reading(station.measurements)


def get_sea_readings(station_name):
    raw_data = get_data_from(SEA_TEMPERATURE_SOURCE)

    weather_stations = extract_stations_from(raw_data) 
    station = weather_stations.get(station_name)

    if not station:
        return (f"Podaci za stanicu {station_name} nisu dostupni.", "-")
    return find_current_reading(station.measurements)


def get_general_readings(station_name):
    weather_stations = {}
    raw_data = get_data_from(GENERAL_WEATHER_SOURCE)

    current_date = raw_data.get("DatumTermin").get("Datum")
    read_time = raw_data.get("DatumTermin").get("Termin")

    weather_stations = extract_stations_from(raw_data)
    station = weather_stations.get(station_name)

    return station.measurements, current_date, read_time


def output_html(
    city,
    current_date,
    read_time,
    uv_read_time,
    uv_index,
    general_data,
    sea_read_time,
    sea_temp
):
    """Pass the parameters to Jinja template and render HTML page."""

    env = Environment(loader=FileSystemLoader("src"))
    page = env.get_template("template.html").render(
        city=city,
        date=current_date,
        read_time=read_time,
        general_data=general_data,
        uv_index=uv_index,
        uv_read_time=uv_read_time,
        sea_temp=sea_temp,
        sea_read_time=sea_read_time,
    )

    with open("src/index.html", "w") as f:
        f.write(page)


if __name__ == "__main__":
    city = "Malinska"  # TODO: make every city available as a selection
    uv_read_time, uv_index = get_current_uv_reading(city)
    general_data, current_date, read_time = get_general_readings(city)
    sea_read_time, sea_temp = get_sea_readings(city)

    output_html(
        city=city,
        current_date=current_date,
        read_time=read_time,
        general_data=general_data,
        uv_index=uv_index,
        uv_read_time=uv_read_time,
        sea_temp=sea_temp,
        sea_read_time=sea_read_time,
    )
