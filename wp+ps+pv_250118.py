import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

# eigene Module:
import pv_profil, lastprofile_VDI4655, temperatur_aussen, try_region, heizkurve, berechnen_wp


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
lastprofil_h= lastprofil_h.join(lastprofil)

## WP Größe
wp_groesse = berechnen_wp.get_waermepumpe(heizlast)

## Heizkurve
heizkennlinie, T_soll, T_n_vor, T_n_rueck = heizkurve.get_heizkurve(heizung, lastprofil_h['T_aussen'], T_n_aussen)
lastprofil_h['T_vor'] = heizkennlinie['T_vor']
lastprofil_h['T_rueck'] = heizkennlinie['T_rueck']
# Plot  mit heizkurve.plot_heizkurve(heizkurve) 

## Heizleistung Auslegung & Theoretisch
heizleistung = heizkurve.get_heizleistung(T_n_aussen, wp_groesse, T_soll)
heizleistung_auslegung = heizkurve.get_heizleistung_profil(lastprofil_h, heizleistung)
# Plot Heizleistung in Abhängigkeit der Außentemperatur: heizkurve.plot_heizleistung
lastprofil_h['Heizleistung'] = heizleistung_auslegung['Heizleistung Auslegung']

## COP für T_vor und T_aussen
lastprofil_h['COP'] = heizkurve.get_cop(wp_groesse, lastprofil_h)

## Pufferspeicher Größe, PS Verlust und Wärmegehalt
V_ps, PS_verlust, Q_ps = berechnen_wp.get_pufferspeicher(heizlast, T_n_vor, T_n_rueck)

## WP und PS Zusammenfügen
lastprofil_h, P_el, COP = berechnen_wp.ohne_pv(lastprofil_h, Q_ps, PS_verlust)
print('Strombedarf WP: ', P_el)
print('COP bzw. JAZ: ', COP)
stromkosten = round(P_el*0.358, 2)
print('Stromkosten: ', stromkosten)

## WP und PV
lastprofil_h, ersparniss = berechnen_wp.mit_pv(lastprofil_h, pv)
print('Strom aus PV: ', )
print('Strom aus Netz: ', )
stromkosten_pv = round()
print('Stromkosten mit PV: ', stromkosten_pv)
print('Einsparung: ', stromkosten-stromkosten_pv)

