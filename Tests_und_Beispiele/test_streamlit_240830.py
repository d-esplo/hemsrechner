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

# streamlit run test_streamlit_240830.py --server.port 5997

# Titel
st.title('Berechnungstool')
st.header('Stromkosten sparen mit einer PV-Anlage')

# Variable Abfrage
plz = st.text_input('#### Postleitzahl: ')
anlage_groesse = st.text_input('Größe der PV-Anlage in kWp: ')
strom_bedarf_str = st.text_input('Jährliche Strombedarf in kWh: ')
bs = st.radio("Batteriespeicher?", ("Ja", "Nein"))

## Berechnung PV Ertrag - pvlib ##
# Standort
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = a['latitude']
longitude = a['longitude']
year = 2016
# Get hourly solar irradiation and modeled PV power output from PVGIS
data, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2016, end=2016, surface_tilt=35,
                                                    pvcalculation=True, peakpower=anlage_groesse, mountingplace='building', loss = 0)  

data.set_index(pd.date_range(datetime.datetime(year, 1, 1, 0), periods= len(data), freq="h"), inplace=True)

ertrag = round(data['P'].sum()/1000,2)

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

if bs == 'Nein':
    # Ersparniss ohne BS
    # pv-stromprofil
    df['sub'] = df['pv']-df['ac_consumption']

    # Netzbezug
    pd.options.mode.copy_on_write = True # compute without SettingWithCopyingWarning: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
    zero = 0 
    df['netzbezug'] = df['sub'].abs().where(df['sub'] < zero, other = 0)

    # PV Eigenverbrauch
    df['eigenverbrauch'] = df['ac_consumption'].where(df['sub'] > zero, other = 0)

    # PV Einspeisung
    df['einspeisung'] = df['sub'].where(df['sub'] > zero, other = 0)
else:
    batterie_groesse = st.text_input('Batteriespeicher Größe in kWh: ')
    batterie_groesse = pd.to_numeric(batterie_groesse, errors='coerce')
    c_rate = 1
    lade_leistung = c_rate * batterie_groesse
    min_soc = 1
    max_soc = batterie_groesse
    batterie_soc = 5
    lade_n = 0.96 # Charge efficiency

    # Neue Spalten in DataFrame für die Ergebnisse
    df['batterie_soc'] = 0.0
    df['batterie_laden'] = 0.0
    df['battery_entladen'] = 0.0
    df['einspeisung'] = 0.0
    df['pv_ueberschuss'] = 0.0
    df['netzbezug'] = 0.0 
    df['eigenverbrauch'] = 0.0
    
    # Simulation Schleife
    for timestamp in df.index:
        pv_production = df.loc[timestamp,'pv']
        ac_consumption = df.loc[timestamp,'ac_consumption'] # Verbrauchsstromprofil

        if pv_production >= ac_consumption:
            # Surplus PV production
            surplus = pv_production - ac_consumption

            # Charge the battery with the surplus, limited by the charging power and max_soc
            lade_potential = min(surplus * lade_n, lade_leistung)
            charge_to_battery = min(lade_potential, max_soc - batterie_soc)

            # Update battery state of charge
            batterie_soc += charge_to_battery

            # Calculate excess PV after charging battery
            pv_excess = surplus - (charge_to_battery / lade_n)

            # Energy to be exported to the grid
            grid_export = pv_excess

            # Update DataFrame
            df.loc[timestamp, 'battery_laden'] = charge_to_battery
            df.loc[timestamp, 'einspeisung'] = grid_export
            df.loc[timestamp, 'pv_ueberschuss'] = pv_excess
            df.loc[timestamp, 'netzbezug'] = 0.0  # No grid import in surplus case
            df.loc[timestamp, 'eigenverbrauch'] = ac_consumption

        else:
            # PV production is less than AC consumption
            shortfall = ac_consumption - pv_production

            # Discharge battery to meet the shortfall, limited by discharging power and min_soc
            discharge_needed = min(shortfall/lade_n, lade_leistung)
            discharge_from_battery = min(discharge_needed, batterie_soc-min_soc)

            # Actual energy supplied to AC from battery
            energy_from_battery = discharge_from_battery * lade_n

        
            # Update battery state of charge
            batterie_soc -= discharge_from_battery
            batterie_soc = max(batterie_soc, min_soc) # Ensure SOC does not drop below min_soc ## TAL VEZ NO SEA NECESARIO

            # Calculate any remaining shortfall after battery discharge
            remaining_shortfall = shortfall - energy_from_battery

            # Energy imported from the grid to cover the remaining shortfall
            grid_import = remaining_shortfall if remaining_shortfall > 0 else 0.0

            # Update DataFrame
            df.loc[timestamp, 'battery_entladen'] = discharge_from_battery
            df.loc[timestamp, 'netzbezug'] = grid_import
            df.loc[timestamp, 'einspeisung'] = 0.0  # No grid export in deficit case
            df.loc[timestamp, 'pv_ueberschuss'] = 0.0  # No excess PV in deficit case
            df.loc[timestamp, 'eigenverbrauch'] = energy_from_battery + pv_production

        # Update SOC in the DataFrame
        df.loc[timestamp, 'batterie_soc'] = batterie_soc

# Stromkosten mit PV
# Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
strompreis = 0.4135
netzbezug = round(sum(df['netzbezug']))
stromkosten = round(netzbezug * strompreis, 2)

# Stromkosten ohne PV
verbrauch = round(sum(df['ac_consumption']), 2)
stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

# Einspeisevergütung - Gewinn
# Einspeisevergütung 2024: Feb-Aug: 8,1 ct, Aug-Feb25: 8 ct (https://photovoltaik.org/kosten/einspeiseverguetung)
einspeiseverguetung = 0.08
einspeisung = round(sum(df['einspeisung']))
verguetung = round(einspeisung * einspeiseverguetung, 2)

# Ersparnis
einsparung = round(stromkosten_ohne_pv - (stromkosten - verguetung), 2)
    
# Ergebnisse
st.write('## PV Ertrag [kWh/Jahr]: ', round(ertrag))
st.write('### Eigenverbrauch [kWh/Jahr]: ', round(sum(df['eigenverbrauch'])))
st.write('### Netzeinpeisung [kWh/Jahr]: ', einspeisung)
st.write('### Einspeisevergütung [€/Jahr]: ', verguetung)
st.write('### Netzbezug [kWh/Jahr]: ', netzbezug)
st.write('### Strombezugkosten [€/Jahr]: ', stromkosten)
st.write('## Einsparung mit PV und BS [€/Jahr]: ', einsparung)


# st.slider("Pick a number", 0, 100)
# x = st.slider('x') 

''
# # Plot 
'## Tag: 1. Juli'
tag = df.loc['2016-07-01 00:00:00':'2016-07-01 23:00:00', ['pv','einspeisung', 'netzbezug','eigenverbrauch','ac_consumption','batterie_soc']]
st.line_chart(tag)
''
'## 1. Woche: Juli'
woche = df.loc['2016-07-01 00:00:00':'2016-07-07 23:00:00',['pv','einspeisung', 'netzbezug','eigenverbrauch','ac_consumption','batterie_soc']]
st.line_chart(woche)
''
# '## Pro Woche'


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







