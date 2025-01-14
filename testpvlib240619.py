import pvlib
import pandas as pd # 'as pd' to change alias from pandas to pd
import matplotlib.pyplot as plt
import pgeocode

# Standort
plz = input("PLZ eingeben: ")
anlage_groesse = input('Größe der PV-Anlage in kWp: ')
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = a['latitude']
longitude = a['longitude']

# Get hourly solar irradiation and modeled PV power output from PVGIS
data, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2016, end=2016, surface_tilt=35,
                                                    pvcalculation=True, peakpower=anlage_groesse, mountingplace='building', loss = 0)  

ertrag = data['P'].sum()
print(round(ertrag/1000, 2), 'kWh')

plt.plot(data['P'])
plt.show()


