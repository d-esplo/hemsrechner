import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

# eigene Module:
import pv_profil, lastprofile_VDI4655, temperatur_aussen, try_region, heizkurve, berechnen_wp

## Abfrage - Inputs
# plz = int(input("PLZ eingeben: "))
# baujahr = str(input("Baujahr EFH eingeben: "))
# flaeche = int(input('Hausfläche ca.: '))
# heizung = str(input('Heizkörper oder Fußbodenheizung? '))
# anzahl_personen = int(input("Anzahl an Hausbewohner: "))
# strombedarf = int(input("Strombedarf [kW]: "))
# anlage_groesse = int(input('Größe der PV-Anlage in kWp: '))

plz = 40599
baujahr = 'Nach 2002'
flaeche = 200
heizung = 'Fußbodenheizung'
anzahl_personen = 3
strombedarf = 0
anlage_groesse = 10

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
lastprofil_h = heizkurve.get_heizleistung_profil(lastprofil_h, heizleistung)
# Plot Heizleistung in Abhängigkeit der Außentemperatur: heizkurve.plot_heizleistung

## COP für T_vor und T_aussen
lastprofil_h = heizkurve.get_cop(wp_groesse, lastprofil_h)

## Pufferspeicher Größe, PS Verlust und Wärmegehalt
V_ps, PS_verlust, Q_ps = berechnen_wp.get_pufferspeicher(heizlast, T_n_vor, T_n_rueck)

## Lastprofil WP und PS
lastprofil_h, P_el, COP = berechnen_wp.ohne_pv(lastprofil_h, Q_ps, PS_verlust)
print('Strombedarf WP: ', P_el)
print('COP bzw. JAZ: ', round(COP,2))

## Lastprofil WP und PV
lastprofil_h = berechnen_wp.mit_pv(lastprofil_h, pv)

## Kosten und Ersparnis
strompreis = 0.358
kosten_ohne, kosten_mit, ersparnis = berechnen_wp.kosten(lastprofil_h, strompreis)
print('Stromkosten WP ohne PV: ', kosten_ohne)
print('Stromkosten WP mit PV: ', kosten_mit)
print('Einsparung mit PV: ', ersparnis)



