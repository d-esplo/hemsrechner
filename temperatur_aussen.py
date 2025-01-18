from meteostat import Point, Hourly
import pandas as pd
import pgeocode

def get_hourly_temperature(plz, jahr):
    # PLZ in lat & lon umwandeln
    nomi = pgeocode.Nominatim('de') 
    a = nomi.query_postal_code(plz)
    lat = a['latitude']
    lon = a['longitude']

    # Standort-Objekt erstellen
    location = Point(lat, lon)

    # Jahr
    start = pd.Timestamp(f'{jahr}-01-01 00:00:00')
    end = pd.Timestamp(f'{jahr}-12-31 23:00:00')

    # Abfrage der stündlichen Temperaturdaten
    data = Hourly(location, start, end)
    data = data.fetch()

    # Nur Temperatur relevant
    temperature_data = data[['temp']]

    # Nur Temperaturdaten zurückgeben
    return temperature_data

