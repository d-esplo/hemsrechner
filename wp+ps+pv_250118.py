import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np

# eigene Module:
import pv_profil, lastprofile_VDI4655, temperatur_aussen, try_region, heizkurve


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
lastprofil_h['Wärmegehalt PS'] = np.nan
lastprofil_h['Ladezustand PS'] = np.nan
lastprofil_h['Heizleistung neu'] = np.nan
lastprofil_h['temp_mittel'] = lastprofil_h['T_aussen'].rolling(window=48, min_periods=1).mean()
lastprofil_h['Wärmebedarf_mittel'] = lastprofil_h['Wärmebedarf'].rolling(window=48, min_periods=1).mean()

# Set 1. Reihe 
t_amb.iloc[0, t_amb.columns.get_loc('Wärmegehalt PS')] = Q_ps  
t_amb.iloc[0, t_amb.columns.get_loc('Ladezustand PS')] = 1 
t_amb.iloc[0, t_amb.columns.get_loc('Heizleistung neu')] = t_amb.iloc[0, t_amb.columns.get_loc('Heizleistung')]

for time in t_amb.index[1:]:  # ab der zweiten Zeile
    previous_time = time - pd.Timedelta(hours=1)
    
    # Bedingungsüberprüfung und Debugging
    # print(f"Verarbeite Zeitstempel: {time}, vorheriger Zeitstempel: {previous_time}")
    # print(f"Wärmegehalt PS (vorher): {t_amb.loc[previous_time, 'Wärmegehalt PS']}, Wärmebedarf: {t_amb.loc[time, 'Wärmebedarf']}")
    
    if t_amb.loc[time, 'temp_mittel'] <= 15: #and t_amb.loc[time, 'Wärmebedarf_mittel'] >= 1.8:
        if t_amb.loc[time, 'Wärmebedarf'] == 0:
            t_amb.loc[time, 'Heizleistung neu'] = 0
            t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] - t_amb.loc[time, 'Wärmebedarf'] - PS_verlust
        elif t_amb.loc[time, 'Wärmebedarf'] > t_amb.loc[time, 'Heizleistung']:
            t_amb.loc[time, 'Heizleistung neu'] = t_amb.loc[time, 'Wärmebedarf']
            t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] - t_amb.loc[time, 'Wärmebedarf'] - PS_verlust + t_amb.loc[time, 'Heizleistung neu']
        elif t_amb.loc[previous_time, 'Wärmegehalt PS'] > t_amb.loc[time, 'Wärmebedarf']:
            # print("Wärmegehalt PS > Wärmebedarf, Heizleistung neu = 0")
            t_amb.loc[time, 'Heizleistung neu'] = 0
            t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] - t_amb.loc[time, 'Wärmebedarf'] - PS_verlust
        elif t_amb.loc[previous_time, 'Wärmegehalt PS'] < t_amb.loc[time, 'Wärmebedarf']:
            # print("Wärmegehalt PS < Wärmebedarf...")
            if Q_ps - t_amb.loc[previous_time, 'Wärmegehalt PS'] > t_amb.loc[time, 'Heizleistung']:
                # print("Q_ps - Wärmegehalt PS > Heizleistung, Heizleistung neu angepasst")
                t_amb.loc[time, 'Heizleistung neu'] = t_amb.loc[time, 'Heizleistung'] + Q_ps - t_amb.loc[previous_time, 'Wärmegehalt PS']
                t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] + t_amb.loc[time, 'Heizleistung neu'] - t_amb.loc[time, 'Wärmebedarf'] - PS_verlust
                # print("Heizleistung neu = Heizleistung + Lade PS mehr")
            else:
                # print("Heizleistung neu = Heizleistung")
                t_amb.loc[time, 'Heizleistung neu'] = t_amb.loc[time, 'Heizleistung']
                t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] + t_amb.loc[time, 'Heizleistung neu'] - t_amb.loc[time, 'Wärmebedarf'] - PS_verlust
    else:
        # print("T_mittel > 15° <- wird nicht geheizt")
        t_amb.loc[time, 'Heizleistung neu'] = 0
        t_amb.loc[time, 'Wärmegehalt PS'] = t_amb.loc[previous_time, 'Wärmegehalt PS'] - PS_verlust 

    # Wärmegehalt darf nicht negativ sein
    if t_amb.loc[time, 'Wärmegehalt PS'] <= 0:
        t_amb.loc[time, 'Wärmegehalt PS'] = 0

    # Berechnung des Ladezustands
    ladezustand = t_amb.loc[time, 'Wärmegehalt PS'] / Q_ps
    if ladezustand > 1:
        # print("Ladezustand > 1, setze Ladezustand auf 1")
        t_amb.loc[time, 'Ladezustand PS'] = 1
    elif ladezustand <= 0:
        # print(f"Ladezustand <= 0, setzte 0")
        t_amb.loc[time, 'Ladezustand PS'] = 0
    else:
        t_amb.loc[time, 'Ladezustand PS'] = ladezustand

t_amb.loc[t_amb['Heizleistung neu'] == 0, 'COP'] = 0
# Filtere die Werte, bei denen Heizleistung neu > 0
cop_filtered = t_amb[t_amb['Heizleistung neu'] > 0]['COP']
cop_mean = cop_filtered.mean()

t_amb['elekt. Leistungaufnahme'] = t_amb['Heizleistung neu']/t_amb['COP']
t_amb['therm. Entnahmelesitung'] = t_amb['Heizleistung'] - t_amb['elekt. Leistungaufnahme']

print('P_el [kW/a]: ', round(t_amb['elekt. Leistungaufnahme'].sum(), 2))
print('Stromkosten WP [€/a]:', round(t_amb['elekt. Leistungaufnahme'].sum()*0.358, 2)) # Strompreis Dezember 24 Bestandkunden €/kWh
print('COP: ', round(cop_mean, 2))