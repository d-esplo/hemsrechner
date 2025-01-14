import pvlib
import pandas as pd # 'as pd' to change alias from pandas to pd
import matplotlib.pyplot as plt
import pgeocode

# For demandlib
import datetime
from datetime import time as settime
import numpy as np
from demandlib import bdew
import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles
from workalendar.europe import Germany

import streamlit as st

# trying to reduce warnings
import os
import warnings

if os.environ.get('STREAMLIT_SERVER_ADDRESS', 'localhost') == 'localhost':
    warnings.filterwarnings("ignore")

# streamlit run test_streamlit_240725.py --server.port 5998

# Titel
st.write('# Berechnungstool')
st.write('## Stromkosten sparen mit einer PV-Anlage')

# Variable Abfrage
plz = st.text_input('Postleitzahl: ')
anlage_groesse = st.text_input('Größe der PV-Anlage in kWp: ')
strom_bedarf_str = st.text_input('Jährliche Strombedarf in kWh: ')

## Berechnung PV Ertrag - pvlib ##
# Standort
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = 90
longitude = 0.0
latitude = a['latitude']
longitude = a['longitude']
year = 2016
# Get hourly solar irradiation and modeled PV power output from PVGIS
data, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2016, end=2016, surface_tilt=35,
                                                    pvcalculation=True, peakpower=anlage_groesse, mountingplace='building', loss = 0)  

data.set_index(pd.date_range(datetime.datetime(year, 1, 1, 0), periods= len(data), freq="h"), inplace=True)

ertrag = round(data['P'].sum()/1000,2)
st.write('## PV Ertrag [kWh/Jahr]: ', ertrag)

## Stromprofil - demandlib ##
# Get holidays
cal = Germany()
holidays = dict(cal.holidays(year))

strom_bedarf = float(strom_bedarf_str)
ann_el_demand_per_sector = {
    "h0_dyn": strom_bedarf,
}

# read standard load profiles
e_slp = bdew.ElecSlp(year, holidays=holidays)

# multiply given annual demand with timeseries
strom_profil = e_slp.get_profile(ann_el_demand_per_sector)

column = []
df = pd.DataFrame(column)
df['ac_consumption']= strom_profil.resample("h").mean()
df['pv'] = data['P'].div(1000)

# Ersparniss
# pv-stromprofil
df['sub'] = df['pv']-df['ac_consumption']

# Netzbezug
pd.options.mode.copy_on_write = True # compute without SettingWithCopyingWarning: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy

zero = 0 
df['Netzbezug'] = df['sub'].abs().where(df['sub'] < zero, other = 0)
netzbezug_j = df['Netzbezug'].sum()

# PV Eigenverbrauch
df['Eigenverbrauch'] = df['ac_consumption'].where(df['sub'] > zero, other = 0)
eigenverbrauch_j = df['Eigenverbrauch'].sum()

# PV Einspeisung
df['Einspeisung'] = df['sub'].where(df['sub'] > zero, other = 0)
einspeisung_j = df['Einspeisung'].sum()

# Ergebnisse
st.write('### Netzeinpeisung [kWh/Jahr]: ', round(einspeisung_j))
st.write('### Eigenverbrauch [kWh/Jahr]: ', round(eigenverbrauch_j))
st.write('### Netzbezug [kWh/Jahr]: ', round(netzbezug_j))

# # Plot Stromprofil
# df = strom_profil.resample("h").mean()

# # PV Profil in Strom Profil DataFrame hinzufügen (in kWh)
# # Neue Spalte in df 
# df['pv'] = data['P'].div(1000)
# # st.line_chart(df)

# elec_month = strom_profil.resample('ME').mean()
# elec_month['pv'] = data['P'].resample('ME').mean().div(1000)
# st.bar_chart(elec_month)

# # elec_day = df.loc['2016-07-01 00:00:00':'2016-07-01 23:00:00', ['pv', 'h0_dyn']]
# # st.line_chart(elec_day)

# # maybe resample sum per week or month?
# el_month = elec_demand.resample('ME').sum()
# el_month['pv'] = data['P'].resample('ME').sum().div(1000)
# st.bar_chart(el_month)

# el_week = elec_demand.resample('W').sum()
# el_week['pv'] = data['P'].resample('W').sum().div(1000)
# st.bar_chart(el_week)






