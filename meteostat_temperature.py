from meteostat import Point, Hourly
import pandas as pd
import pgeocode

def get_hourly_temperature(lat, lon, year, filename='hourly_temperature.csv'):
    # Standort-Objekt erstellen
    location = Point(lat, lon)

    # Jahr
    start = pd.Timestamp(f'{year}-01-01 00:00:00')
    end = pd.Timestamp(f'{year}-12-31 23:00:00')

    # Abfrage der stündlichen Temperaturdaten
    data = Hourly(location, start, end)
    data = data.fetch()

    # Nur Temperatur relevant
    temperature_data = data[['temp']]

    # Speichern in CSV Datei
    temperature_data.to_csv(filename, index=True)

    # Nur Temperaturdaten zurückgeben
    return temperature_data

# latitude = 52.52
# longitude = 13.405
year = 2014

# or with PLZ
plz = 40599
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = a['latitude']
longitude = a['longitude']

filename = f'T_amb_{plz}_{year}.csv'
temperatures_2024 = get_hourly_temperature(latitude, longitude, year, filename)
