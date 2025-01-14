# For pvlib
import pvlib
import pandas as pd # 'as pd' to change alias from pandas to pd
import matplotlib.pyplot as plt
import pgeocode

# Input
plz = input("PLZ eingeben: ")
anlage_groesse = input('Größe der PV-Anlage in kWp: ')
strombedarf = input("Jährliche Strombedarf in kWH: ")
strombedarf = float(strombedarf)

# Standort
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = a['latitude']
longitude = a['longitude']

# Get hourly solar irradiation and modeled PV power output from PVGIS
data, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2016, end=2016, surface_tilt=35,
                                                    pvcalculation=True, peakpower=anlage_groesse, mountingplace='building', loss = 0)  

ertrag = data['P'].sum()
print(round(ertrag/1000, 2), 'kWh')

# Plot PV power
plt.plot(data['P'])
plt.show()

# For demandlib
import datetime
from datetime import time as settime
import numpy as np
from demandlib import bdew
import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles
from workalendar.europe import Germany

cal = Germany()
year = 2016
holidays = dict(cal.holidays(year))

ann_el_demand_per_sector = {
    "h0": strombedarf,
    "h0_dyn": strombedarf,
}

# read standard load profiles
e_slp = bdew.ElecSlp(year, holidays=holidays)

# multiply given annual demand with timeseries
elec_demand = e_slp.get_profile(ann_el_demand_per_sector)

# You will have to divide the result by 4 to get kWh. 
print(elec_demand.sum() / 4)

# Plot demand
elec_demand_resampled = elec_demand.resample("h").mean() 
ax = elec_demand_resampled.plot()
ax.set_xlabel("Date")
ax.set_ylabel("Power demand")
plt.show()

print(elec_demand_resampled)




