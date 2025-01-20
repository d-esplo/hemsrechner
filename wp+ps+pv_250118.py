import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

# eigene Module:
import pv_profil, lastprofile_VDI4655, temperatur_aussen, try_region, heizkurve, berechnen_pvwpps



## Abfrage - Inputs
plz = input("PLZ eingeben: ")
baujahr = input("Baujahr EFH eingeben: ")
flaeche = input('Hausfläche ca.: ')
heizung = input('Heizkörper oder Fußbodenheizung? ')
anzahl_personen = input("Anzahl an Hausbewohner: ")
strombedarf = input("Strombedarf [kW]: ")
anlage_groesse = input('Größe der PV-Anlage in kWp: ')

## PV Profil
jahr = 2014
pv = pv_profil.get_pv_profil(plz, jahr, anlage_groesse)

## Jahresenergiebedarf: 
heizlast, waermebedarf, twebedarf, strombedarf = lastprofile_VDI4655.get_jahresenergiebedarf(baujahr, flaeche, anzahl_personen, strombedarf)

## TRY Region und T_n_aussen
TRY_region, T_n_aussen = try_region.get_try_t_n_aussen(plz)

## Aussen Temperatur
t_aussen = temperatur_aussen.get_hourly_temperature(plz, jahr)
lastprofil_h = pd.DataFrame()
lastprofil_h['T_aussen'] = t_aussen

## Lastprofile erstellen
lastprofil = lastprofile_VDI4655.get_lastprofile(waermebedarf, strombedarf, twebedarf, flaeche, TRY_region, anzahl_personen)
lastprofil_res = lastprofil.resample('h').sum()
lastprofil_h= lastprofil_h.join(lastprofil_res)

## WP Größe
if heizlast <= 7:
    wp_groesse = 6
    wp = 'Nibe F2040-6'
elif heizlast <= 9:
    wp_groesse = 8
    wp = 'Nibe F2040-8'
elif heizlast <=13:
    wp_groesse = 12
    wp = 'Nibe F2040-12'
else:
    wp_groesse = 16
    wp = 'Nibe F2040-16'

## Heizkurve
heizkennlinie, T_soll, T_n_vor, T_n_rueck = heizkurve.get_heizkurve(heizung, lastprofil_h['T_aussen'], T_n_aussen)
lastprofil_h['T_vor'] = heizkennlinie['T_vor']
lastprofil_h['T_rueck'] = heizkennlinie['T_rueck']

## Heizleistung Auslegung & Theoretisch
heizleistung = heizkurve.get_heizleistung(T_n_aussen, wp_groesse, T_soll)
lastprofil_h['Heizleistung'] = heizleistung['Heizleistung Auslegung']

## COP
lastprofil_h['COP'] = heizkurve.get_cop(wp_groesse, lastprofil_h['T_aussen'], lastprofil_h['T_vor'])

## Pufferspeicher Größe
V_ps_einfach = 20 * heizlast 
VPS_100 = 100
VPS_200 = 200
VIH_300 = 300
TWL_PR_500 = 500

if V_ps_einfach > VPS_200:
    if V_ps_einfach <= VIH_300:
        V_ps = VIH_300
        PS_verlust = 1.52/24 # kWh/24h
    else:
        V_ps = TWL_PR_500
        PS_verlust = 1.4/24 # kWh/24h
elif V_ps_einfach <= VPS_200:
    if V_ps_einfach <= VPS_100:
        V_ps = VPS_100
        PS_verlust = 0.81/24 # kWh/24h
    else:
        V_ps= VPS_200
        PS_verlust = 1.4/24 # kWh/24h

## Wärmegehalt Pufferspeicher
dichte = 1 # kg/m^3
c_wasser = 4.18 # kJ/(kg·K)
Q_ps = round(V_ps*dichte*c_wasser*(T_n_vor - T_n_rueck)/3600, 3)

## WP und PS Zusammenfügen
