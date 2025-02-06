import numpy as np
import pandas as pd
import streamlit as st
import heizkurve

def get_waermepumpe(heizlast):
    if heizlast <= 5:
        wp_groesse = 6
        nenn_heizleistung = 5.3
        wp = 'Nibe F2040-6'
    elif heizlast <= 7:
        wp_groesse = 8
        nenn_heizleistung = 7
        wp = 'Nibe F2040-8'
    elif heizlast <= 10:
        wp_groesse = 12
        nenn_heizleistung = 10
        wp = 'Nibe F2040-12'
    else:
        wp_groesse = 16
        nenn_heizleistung = 14
        wp = 'Nibe F2040-16'
    return wp_groesse, nenn_heizleistung

def get_pufferspeicher(heizlast, T_n_vor, T_n_rueck):
    # Pufferspeicher auswählen 
    # Vaillant https://www.vaillant.de/heizung/produkte/pufferspeicher-359745.html#specification
    # VPS R 100/1 M - Bereitschaftswärmeverlust Speicher: 0,81 kWh/24h
    # VPS R 200/1 B - Bereitschaftswärmeverlust Speicher: 1,4 kWh/24h
    # VIH RW 300 - Bereitschaftswärmeverlust Speicher: 1,52 kWh/24
    # TWL Pufferspeicher PR 500 Liter - Bereitschaftswärmeverlust Speicher: 1,4 kWh/24h -- https://www.solardirekt24.de/TWL-Pufferspeicher-PR-500-Liter-OEkoLine-A-Isolierung-PR.0500.Iso-A
    VPS_100 = 100
    VPS_200 = 200
    VIH_300 = 300
    TWL_PR_500 = 500

    V_sp_einfach = 20*heizlast

    if V_sp_einfach > VPS_200:
        if V_sp_einfach <= VIH_300:
            V_ps = VIH_300
            PS_verlust = 1.52/24 # kWh/24h
        else:
            V_ps = TWL_PR_500
            PS_verlust = 1.4/24 # kWh/24h
    elif V_sp_einfach <= VPS_200:
        if V_sp_einfach <= VPS_100:
            V_ps = VPS_100
            PS_verlust = 0.81/24 # kWh/24h
        else:
            V_ps= VPS_200
            PS_verlust = 1.4/24 # kWh/24h

    # Wärmegehalt Pufferspeicher
    dichte = 1 # kg/m^3
    c_wasser = 4.18 # kJ/(kg·K)
    Q_ps = round(V_ps*dichte*c_wasser*(T_n_vor - T_n_rueck)/3600, 3)

    return V_ps, PS_verlust, Q_ps

# Berechnen - immer vorher df aus def ohne_pv erstellen 
def ohne_2(df, Q_ps, PS_verlust):
## WP und PS Zusammenfügen
    df['Wärmegehalt PS'] = np.nan
    df['Q_ps_neu'] = 0.0
    df['Ladezustand PS'] = np.nan
    df['Heizleistung neu'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=24, min_periods=1).mean()
    df['Wärmeverlust'] = np.nan
    df['State'] = 0

    waerme_ps = Q_ps
    V = 300
    d = 1
    c_wasser = 4.18

    for i, row in df.iterrows():  # ab der zweiten Zeile
        temp_mittel = row['temp_mittel']
        heizwaermebedarf = row['Heizwärmebedarf']
        heizleistung = row['Heizleistung']
        t_d = row['T_vor'] - row['T_rueck']
        verlust = 0.0
        lade_ps = 0.0
        heizleistung_neu = 0.0
        state = 0.0
        hz = 0.0
        ladezustand = 1
        

        #if temp_mittel <= 15:

    return df

def ohne_pv(df, Q_ps, PS_verlust, nenn_heizleistung):
    ## WP und PS Zusammenfügen
    df['Wärmegehalt PS'] = np.nan
    df['Q_ps_neu'] = 0.0
    df['Ladezustand PS'] = np.nan
    df['Heizleistung neu'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=24, min_periods=1).mean()
    df['Wärmeverlust'] = np.nan
    df['State'] = 0
    
    # df['Wärmebedarf_mittel'] = df['Heizwärmebedarf'].rolling(window=48, min_periods=1).mean()

    # Set 1. Reihe 
    # df.iloc[0, df.columns.get_loc('Wärmegehalt PS')] = Q_ps  
    # df.iloc[0, df.columns.get_loc('Ladezustand PS')] = 1 
    # df.iloc[0, df.columns.get_loc('Heizleistung neu')] = df.iloc[0, df.columns.get_loc('Heizleistung')]

    max_heizleistung = nenn_heizleistung
    waerme_ps = Q_ps
    V = 300
    d = 1
    c_wasser = 4.18

    for i, row in df.iterrows():  # ab der zweiten Zeile
        temp_mittel = row['temp_mittel']
        heizwaermebedarf = row['Heizwärmebedarf']
        heizleistung = row['Heizleistung']
        t_d = row['T_vor'] - row['T_rueck']
        verlust = 0.0
        lade_ps = 0.0
        heizleistung_neu = 0.0
        state = 0.0
        hz = 0.0
       
        if temp_mittel <= 15:
            deckung = waerme_ps + heizleistung - heizwaermebedarf - PS_verlust 
            if heizwaermebedarf == 0:
                heizleistung_neu = 0
                waerme_ps -= PS_verlust
                state = 1
                if waerme_ps < Q_ps:
                    # PS Laden wenn nicht vollständig geladen
                    heizleistung_neu = heizleistung
                    lade_ps = min(heizleistung_neu, Q_ps-waerme_ps)
                    waerme_ps += lade_ps - PS_verlust
                    verlust = heizleistung_neu - lade_ps
                    state = 2
            elif heizwaermebedarf > 0:
                if deckung < 0:
                    # Heizwärmebedarf wird nicht mit Heizlesitung und PS gedeckt, dann Heizleistung höher stellen
                    hz = heizleistung - deckung
                    heizleistung_neu = min(hz + Q_ps, max_heizleistung)
                    waerme_ps -= (heizwaermebedarf + PS_verlust - heizleistung_neu)
                    state = 3
                elif deckung > 0:
                    # Heizwärmebedarf wird gedeckt und übrige Wärme wird in PS gespeichert
                    heizleistung_neu = heizleistung
                    lade_ps = min(deckung, Q_ps-waerme_ps)
                    waerme_ps += lade_ps - PS_verlust
                    state = 4
                else:
                    # Deckung == 0, also waerme_ps == 0 -> sollten Heizleistung höher stellen damit PS geladen wird, ohne max_heizleistung zu überschreiten
                    heizleistung_neu = min(heizleistung + Q_ps, max_heizleistung)
                    waerme_ps -= (heizwaermebedarf + PS_verlust - heizleistung_neu)
                    state = 5
        else:
            # "T_mittel > 15° <- wird nicht geheizt
            heizleistung_neu = 0
            waerme_ps -= PS_verlust
            state = 6

        # Wärmegehalt darf nicht negativ sein
        if waerme_ps <= 0:
            waerme_ps = 0

        # Berechnung des Ladezustands
        ladezustand = waerme_ps / Q_ps
        # if ladezustand > 1:
        #     # print("Ladezustand > 1, setze Ladezustand auf 1")
        #     ladezustand_ps = 1
        # elif ladezustand <= 0:
        #     # print(f"Ladezustand <= 0, setzte 0")
        #     ladezustand_ps = 0
        # else:
        #     ladezustand_ps = ladezustand

            
     # Assign calculated values back to the DataFrame
        df.loc[i, 'Wärmegehalt PS'] = waerme_ps
        df.loc[i, 'Ladezustand PS'] = ladezustand
        df.loc[i, 'Heizleistung neu'] = heizleistung_neu
        df.loc[i, 'Wärmeverlust'] = verlust
        df.loc[i, 'State'] = state
        df.loc[i, 'Q_ps_neu'] = V*d*c_wasser*t_d/3600

    # Handle rows where Heizleistung neu == 0
    df.loc[df['Heizleistung neu'] == 0, 'COP'] = np.nan
    # df['COP'] = df['COP'].replace(0, np.nan).astype(float)

    # Calculate the mean COP for rows where Heizleistung neu > 0
    cop_filtered = df[df['Heizleistung neu'] > 0]['COP']
    COP = round(cop_filtered.mean(),2)

    # Assign elekt. Leistungaufnahme using the full COP column
    df['elekt. Leistungaufnahme'] = (df['Heizleistung neu'] / df['COP']).fillna(0).astype(float)

    # Handle any potential division by zero
    df['elekt. Leistungaufnahme'].fillna(0, inplace=True)

    # Calculate therm. Entnahmelesitung
    df['therm. Entnahmelesitung'] = df['Heizleistung'] - df['elekt. Leistungaufnahme']

    P_el = round(df['elekt. Leistungaufnahme'].sum(), 2)
    return df, P_el, COP

def mit_pv(df, pv):
    # Benutzen den df aus def ohne_pv, also immer muss vorher der laufen
    # Normalize timezones: remove the timezone for both indices
    pv.index = pv.index.tz_localize(None)
    df.index = df.index.tz_localize(None)

    # Align PV data with the DataFrame index
    pv_aligned = pv.reindex(df.index)

    # Add PV data to the DataFrame
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # Initialize columns for surplus and WP energy from PV
    df['überschuss'] = 0.0
    df['PV to WP'] = 0.0 # Elektrische Leistung für WP aus PV
    df['eigenverbrauch'] = 0.0 
    df['netzbezug'] = 0.0

    # Iterate through rows
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row['elekt. Leistungaufnahme']  # Electrical power for WP
        pv_to_wp =  0
        ueberschuss = 0
        eigenverbrauch = 0
        netzbezug = 0

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag

        # Step 2: Überschuss für WP (prio)
        if ueberschuss > 0 and p_el_wp > 0:
            if ueberschuss >= p_el_wp:
                pv_to_wp = p_el_wp
                ueberschuss -= p_el_wp
                eigenverbrauch += pv_to_wp
            else:
                pv_to_wp = ueberschuss
                ueberschuss = 0
                eigenverbrauch += pv_to_wp
        else:
            pv_to_wp = 0

        netzbezug = (strombedarf - eigenverbrauch) + (p_el_wp - pv_to_wp)
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0
        
        # Assign values to the DataFrame
        df.at[i, 'überschuss'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
        df.at[i, 'netzbezug'] = netzbezug
    return df

def mit_pvbs(df, pv, anlage_groesse, battery_capacity):
    # Normalize timezones: remove the timezone for both indices
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)

    # Align PV data with the DataFrame index
    pv_aligned = pv.reindex(df.index).fillna(0)

    # Add PV data to the DataFrame
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # Initialize columns for battery and WP calculations
    df['battery_soc'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['überschuss'] = 0.0
    df['netzbezug'] = 0.0
    df['eigenverbrauch'] = 0.0
    df['PV to WP'] = 0.0
    df['BS to WP'] = 0.0

    # Battery parameters
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity)

    if anlage_groesse<battery_capacity:
        battery_capacity = anlage_groesse
    
    # Simulation loop
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row.get('elekt. Leistungaufnahme', 0)  # Electrical power for WP (default 0 if not present)
        pv_to_wp =  0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch = 0
        charge_to_battery = 0
        discharge_from_battery = 0
        bs_to_wp = 0

        # Step 1: Überschuss 2 Strombedarf (Prio 1)
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
        
        # Step 2: Überschuss für WP (Prio 2)
        if ueberschuss > 0 and p_el_wp > 0:
            if ueberschuss >= p_el_wp:
                pv_to_wp = p_el_wp
                ueberschuss -= p_el_wp
                eigenverbrauch += pv_to_wp
            else:
                pv_to_wp = ueberschuss
                ueberschuss = 0
                eigenverbrauch += pv_to_wp
        else:
            pv_to_wp = 0

        # Step 3: Überschuss 2 BS (Prio 3)
        if ueberschuss > 0:
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)
            battery_soc += charge_to_battery
            ueberschuss -= (charge_to_battery / charge_efficiency)
            eigenverbrauch += (charge_to_battery / charge_efficiency)
        else:
            charge_to_battery = 0

        charging_power = c_rate * battery_soc * charge_efficiency  # kW

        # Step 4: Strom von Netz?
        energiemangel = strombedarf + p_el_wp - pv_ertrag
        if energiemangel > 0:
            # Entlade Batterie, um Energiemangel zu decken
            discharge_needed = min(energiemangel / discharge_efficiency, charging_power)
            discharge_from_battery = min(discharge_needed, battery_soc - min_soc)
            energy_from_battery = discharge_from_battery * discharge_efficiency
            battery_soc -= discharge_from_battery
            bs_to_wp = p_el_wp - pv_to_wp
            if energy_from_battery >= bs_to_wp:
                bs_to_wp = p_el_wp - pv_to_wp
            else:
                bs_to_wp = 0
            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            remaining_shortfall = energiemangel - energy_from_battery
            netzbezug = max(remaining_shortfall, 0)
        else:
            discharge_from_battery = 0
            netzbezug = 0
        
        ueberschuss = max(0, ueberschuss)
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        # Update DataFrame
        df.loc[i, 'battery_charge'] = charge_to_battery
        df.loc[i, 'battery_discharge'] = discharge_from_battery
        df.loc[i, 'überschuss'] = ueberschuss if ueberschuss > 0 else 0.0
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'PV to WP'] = pv_to_wp
        df.loc[i, 'BS to WP'] = bs_to_wp
        df.loc[i, 'battery_soc'] = battery_soc
    return df

def mit_pvev(df, pv, homeoffice):
    # Passe Index in PV and Index in df an
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV_at_home']
    df['ev distanz'] = ev_aligned['distance_travelled']
    
    # EV Spezifikationen
    ev_effizienz = 191 / 1000  # kWh per km
    batteriekapazitaet = 72  # kWh
    batterie_min = 10  # %
    batterie_max = 80  # %
    min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
    max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
    max_ladeleistung = 11  # kW
    
    # Start EV SOC
    ev_soc = max_batterie_niveau

    df['überschuss'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['PV to WP'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0 

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        p_el_wp = row['elekt. Leistungaufnahme']
        ladeleistung = 0
        pv_to_ev = 0
        pv_to_wp =  0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch = 0

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch

        # Step 2: Überschuss für WP (prio)
        if ueberschuss > 0 and p_el_wp > 0:
            if ueberschuss >= p_el_wp:
                pv_to_wp = p_el_wp
                ueberschuss -= p_el_wp
                eigenverbrauch += pv_to_wp
            else:
                pv_to_wp = ueberschuss
                ueberschuss = 0
                eigenverbrauch += pv_to_wp
                netzbezug += p_el_wp - pv_to_wp
        else:
            pv_to_wp = 0
            netzbezug += p_el_wp
        
        # Step 3: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz*ev_effizienz
            if ev_soc - ev_verbrauch >= min_batterie_niveau:
                ev_soc -= ev_verbrauch
            else:
                ev_distanz = (ev_soc - min_batterie_niveau)/ev_effizienz
                ev_soc = min_batterie_niveau
        
        # Step 4: Lade EV wenn Zuhause
        if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
            ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
            if ueberschuss >= ladeleistung:
                # Überschuss reicht aus, um die gewünschte Ladeleistung abzudecken
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
                eigenverbrauch += pv_to_ev
                ueberschuss -= ladeleistung
            elif ueberschuss > 0:
                # Teilweise Laden mit Überschuss, Rest aus dem Netz
                pv_to_ev = ueberschuss
                netzbezug += ladeleistung - ueberschuss
                ev_soc += ladeleistung
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
            else:
            # Kein Überschuss, Laden komplett aus dem Netz
                ev_soc += ladeleistung
                netzbezug += ladeleistung
        
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        df.at[i, 'ev distanz'] = ev_distanz
        df.at[i, 'überschuss'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'PV to EV'] = pv_to_ev
        df.at[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
        df.at[i, 'netzbezug'] = netzbezug
    return df

def mit_pvbsev(df, pv, anlage_groesse, battery_capacity, homeoffice):
    # Passe Index in PV and Index in df an
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV_at_home']
    df['ev distanz'] = ev_aligned['distance_travelled']
    
    # EV Spezifikationen
    ev_effizienz = 191 / 1000  # kWh per km
    batteriekapazitaet = 72  # kWh
    batterie_min = 10  # %
    batterie_max = 80  # %
    min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
    max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
    max_ladeleistung = 11  # kW
    
    # Start EV SOC
    ev_soc = max_batterie_niveau

    # Neue Spalten für BS, EV und WP
    df['PV to WP'] = 0.0
    df['BS to WP'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0 
    df['PV to EV'] = 0.0
    df['BS to EV'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['battery_soc'] = 0.0
    df['überschuss'] = 0.0
    df['netzbezug'] = 0.0
    df['eigenverbrauch'] = 0.0
    
    # BS Spezifikationen
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity)

    if anlage_groesse<battery_capacity:
        battery_capacity = anlage_groesse

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        p_el_wp = row['elekt. Leistungaufnahme']
        ladeleistung = 0
        pv_to_ev = 0
        pv_to_wp =  0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch_str = 0
        eigenverbrauch_wp = 0
        eigenverbrauch_bs = 0
        eigenverbrauch_ev = 0
        charge_to_battery = 0
        discharge_from_battery = 0
        bs_to_wp = 0
        bs_to_ev = 0
        bs_to_str = 0

        # Step 1: Überschuss nach Strombedarf (Prio 1)
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch_str = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch_str = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch_str

        # Step 2: Überschuss für WP (Prio 2)
        if ueberschuss > 0 and p_el_wp > 0:
            if ueberschuss >= p_el_wp:
                pv_to_wp = p_el_wp
                ueberschuss -= p_el_wp
                eigenverbrauch_wp = pv_to_wp
            else:
                pv_to_wp = ueberschuss
                ueberschuss = 0
                eigenverbrauch_wp = pv_to_wp
                netzbezug += p_el_wp - pv_to_wp
        else:
            pv_to_wp = 0
            netzbezug += p_el_wp
        
        # Step 3: Überschuss 2 BS (Prio 3)
        if ueberschuss > 0:
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)
            battery_soc += charge_to_battery
            ueberschuss -= (charge_to_battery / charge_efficiency)
            eigenverbrauch_bs = (charge_to_battery / charge_efficiency)
        else:
            charge_to_battery = 0
        
        charging_power = c_rate * battery_soc * charge_efficiency  # kW
        
        # Step 4: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz*ev_effizienz
            if ev_soc - ev_verbrauch >= min_batterie_niveau:
                ev_soc -= ev_verbrauch
            else:
                ev_distanz = (ev_soc - min_batterie_niveau)/ev_effizienz
                ev_soc = min_batterie_niveau
        
        # Step 5: Lade EV wenn Zuhause (Prio 4)
        if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
            ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
            if ueberschuss >= ladeleistung:
                # Überschuss reicht aus, um die gewünschte Ladeleistung abzudecken
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
                eigenverbrauch_ev = pv_to_ev
                ueberschuss -= ladeleistung
            elif ueberschuss > 0:
                # Teilweise Laden mit Überschuss, Rest aus dem Netz
                pv_to_ev = ueberschuss
                netzbezug += ladeleistung - ueberschuss
                ev_soc += ladeleistung
                eigenverbrauch_ev = pv_to_ev
                ueberschuss = 0
            else:
            # Kein Überschuss, Laden komplett aus dem Netz
                ev_soc += ladeleistung
                netzbezug += ladeleistung
        
        # Step 6: BS entladen oder von Netz beziehen
        if netzbezug > 0:
            # Entlade Batterie, um Energiemangel zu decken
            discharge_needed = min(netzbezug / discharge_efficiency, charging_power)
            discharge_from_battery = min(discharge_needed, battery_soc - min_soc)
            energy_from_battery = discharge_from_battery * discharge_efficiency
            battery_soc -= discharge_from_battery
            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            remaining_shortfall = netzbezug - energy_from_battery
            netzbezug = max(remaining_shortfall, 0) 

            # Zuweisung von BS Entladung basierend auf Priorität
            netzbezug_wp = max(0, p_el_wp - pv_to_wp)
            netzbezug_ev = max(0, ladeleistung - pv_to_ev)
            netzbezug_str = max(0, strombedarf-pv_ertrag)
            # Verfügbarer Strom aus der Batterie
            remaining_battery = energy_from_battery
            # 1. Prio: Netzbezug für Strombedarf
            if remaining_battery >= netzbezug_str:
                bs_to_str = netzbezug_str
                remaining_battery -= netzbezug_str
            else:
                bs_to_str = remaining_battery
                remaining_battery = 0
            # 2. Prio: Netzbezug für WP
            if remaining_battery > 0:
                if remaining_battery >= netzbezug_wp:
                    bs_to_wp = netzbezug_wp
                    remaining_battery -= netzbezug_wp
                else:
                    bs_to_wp = remaining_battery
                    remaining_battery = 0
            # 3. Prio: Netzbezug für EV
            if remaining_battery > 0:
                if remaining_battery >= netzbezug_ev:
                    bs_to_ev = netzbezug_ev
                    remaining_battery -= netzbezug_ev
                else:
                    bs_to_ev = remaining_battery
                    remaining_battery = 0
        else:
            discharge_from_battery = 0
            netzbezug = 0
        
        ueberschuss = max(0, ueberschuss)
        eigenverbrauch = eigenverbrauch_str+eigenverbrauch_wp+eigenverbrauch_bs+eigenverbrauch_ev
        # Step 7: Überprüfe Überschuss und Netzbezug
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        df.at[i, 'ev distanz'] = ev_distanz
        df.at[i, 'überschuss'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'PV to EV'] = pv_to_ev
        df.at[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
        df.at[i, 'netzbezug'] = netzbezug
        df.loc[i, 'battery_charge'] = charge_to_battery
        df.loc[i, 'battery_discharge'] = discharge_from_battery
        df.loc[i, 'BS to WP'] = bs_to_wp
        df.loc[i, 'BS to EV'] = bs_to_ev
        df.loc[i, 'BS to Haushalt'] = bs_to_str
        df.loc[i, 'battery_soc'] = battery_soc
    return df
    
# Ersparnis 
def ersparnis_pv(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['elekt. Leistungaufnahme']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['elekt. Leistungaufnahme']), 2)
    stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten - verguetung), 2)
    
    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'PV to WP': wp,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def ersparnis_bs(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['elekt. Leistungaufnahme']))
    bs_to_wp = round(sum(df['BS to WP']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    batterie = round(sum(df['battery_charge']))
    wp = round(sum(df['PV to WP']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten_bs = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['elekt. Leistungaufnahme']), 2)
    stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten_bs - verguetung), 2)
    
    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'batterie': batterie,
        'PV to WP': wp,
        'BS to WP': bs_to_wp,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten_bs': stromkosten_bs,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def ersparnis_ev(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['elekt. Leistungaufnahme']))
    ev_strom = round(sum(df['EV Ladung']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie
    wp = round(sum(df['PV to WP']))
    ev = round(sum(df['PV to EV']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten_ev = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['elekt. Leistungaufnahme']+df['EV Ladung']), 2)
    stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten_ev - verguetung), 2)
    
    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'ev': ev_strom,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'PV to WP': wp,
        'PV to EV': ev,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten_bsev': stromkosten_ev,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def ersparnis_evbs(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['elekt. Leistungaufnahme']))
    ev_strom = round(sum(df['EV Ladung']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    batterie = round(sum(df['battery_charge']))
    bs_to_wp = round(sum(df['BS to WP']))
    bs_to_ev = round(sum(df['BS to EV']))
    wp = round(sum(df['PV to WP']))
    ev = round(sum(df['PV to EV']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten_bsev = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['elekt. Leistungaufnahme']+df['EV Ladung']), 2)
    stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten_bsev - verguetung), 2)
    
    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'ev': ev_strom,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'batterie': batterie,
        'PV to WP': wp,
        'PV to EV': ev,
        'BS to WP': bs_to_wp,
        'BS to EV': bs_to_ev, 
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten_bsev': stromkosten_bsev,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

# Print
def print_ersparnis(ergebnisse):
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            print(f"{label}: {ergebnisse[key]}")

    print_if_available('Haushaltsstrombedarf in kWh', 'strombedarf')
    print_if_available('Wärmepumpe Strombedarf in kWh', 'wp')
    print_if_available('EV Strombedarf in kWh', 'ev')
    print_if_available('Jahresertrag in kWh', 'pv')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch')
    print_if_available('Geladene PV-Strom in Wärmepumpe in kWh', 'PV to WP')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'batterie')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV')
    print_if_available('Geladene BS-Strom in Wärmepumoe in kWh', 'BS to WP')
    print('')  # Leere Zeile zur Trennung
    print_if_available('Netzbezug in kWh', 'netzbezug')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung')
    print('')  # Leere Zeile zur Trennung
    print_if_available('Stromkosten ohne PV in €/a', 'stromkosten_ohne_pv')
    print_if_available('Stromkosten mit PV in €/a', 'stromkosten')
    print_if_available('Stromkosten mit PV & BS in €/a', 'stromkosten_bs')
    print_if_available('Stromkosten mit PV & EV in €/a', 'stromkosten_ev')
    print_if_available('Stromkosten mit PV, BS & EV in €/a', 'stromkosten_bsev')
    print_if_available('Einspeisevergütung in €/a', 'verguetung')
    print_if_available('Stromkosten Einsparung in €/a', 'einsparung')

def print_ersparnis_st(ergebnisse):
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            st.write(f"- {label}:   {ergebnisse[key]}")
    
    st.subheader(":blue[Ergebnisse]", divider=True)
    row1 = st.columns(3)  # Erste Zeile: 3 Spalten
    row2 = st.columns(3)  # Zweite Zeile: 3 Spalten

    with row1[0]:
        with st.container(border=True):
            st.write('##### Strombedarf [kWh]')
            print_if_available('Haushalt', 'strombedarf')
            print_if_available('Wärmepumpe', 'wp')
            print_if_available('EV', 'ev')
    
    with row1[1]:
        with st.container(border=True):
            st.write("##### PV [kWh]")
            print_if_available('Jahresertrag', 'pv')
            print_if_available('Eigenverbrauch', 'eigenverbrauch')
            print_if_available('PV to WP', 'PV to WP')
            print_if_available('PV to BS', 'batterie')
            print_if_available('PV to EV', 'PV to EV')

    with row1[2]:
        with st.container(border=True):
            st.write("##### BS [kWh]")
            print_if_available('BS to WP', 'BS to WP')
            print_if_available('BS to EV', 'BS to EV')
    
    with row2[0]:
        with st.container(border=True):
            st.write("##### Netz [kWh]")
            print_if_available('Bezug', 'netzbezug')
            print_if_available('Einspeisung', 'einspeisung')
    
    with row2[1]:
        with st.container(border=True):
            st.write("##### Stromkosten [€/a]")
            print_if_available('ohne PV', 'stromkosten_ohne_pv')
            print_if_available('mit PV', 'stromkosten')
            print_if_available('mit PV & BS', 'stromkosten_bs')
            print_if_available('mit PV & EV', 'stromkosten_ev')
            print_if_available('mit PV, BS & EV', 'stromkosten_bsev')

    with row2[2]:
        with st.container(border=True):
            st.write("##### Einsparung [€/a]")
            print_if_available('Einspeisevergütung', 'verguetung')
            print_if_available('Eigesparte Stromkosten', 'einsparung')
    
# Berechnen mit HEMS
# Basis Programm
def wp_hems(df, pv, Q_ps, PS_verlust, heizlast):
    
    wp_groesse = get_waermepumpe(heizlast)
    df = heizkurve.get_cop(wp_groesse, df.copy())
    
    # Passe Index in PV and Index in df an
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ## WP und PS Zusammenfügen
    df['Wärmegehalt PS'] = np.nan
    df['Ladezustand PS'] = np.nan
    df['Heizleistung neu'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=48, min_periods=1).mean()
    df['PV to WP'] = 0.0 # Elektrische Leistung für WP aus PV
    df['überschuss'] = 0.0
    df['eigenverbrauch'] = 0.0 
    df['netzbezug'] = 0.0
    # df['Wärmebedarf_mittel'] = df['Heizwärmebedarf'].rolling(window=48, min_periods=1).mean()

    # Set 1. Reihe 
    df.iloc[0, df.columns.get_loc('Wärmegehalt PS')] = Q_ps  
    df.iloc[0, df.columns.get_loc('Ladezustand PS')] = 1 
    df.iloc[0, df.columns.get_loc('Heizleistung neu')] = df.iloc[0, df.columns.get_loc('Heizleistung')]

    for time in df.index[1:]:  # ab der zweiten Zeile
        previous_time = time - pd.Timedelta(hours=1)
        temp_mittel = df.at[time, 'temp_mittel']
        heizwaermebedarf = df.at[time, 'Heizwärmebedarf']
        heizleistung = df.at[time, 'Heizleistung']
        heizleistung_neu = df.at[time, 'Heizleistung neu']
        waerme_ps = df.at[time, 'Wärmegehalt PS']
        waerme_ps_p = df.at[previous_time, 'Wärmegehalt PS']
        ladezustand_ps = df.at[time, 'Ladezustand PS']
        cop_60 = df.at[time, 'COP 60']
        cop_40 = df.at[time, 'COP 40']
        strombedarf = df.at[time,'Strombedarf']
        pv_ertrag = df.at[time,'PV Ertrag']
        ueberschuss = 0
        eigenverbrauch = 0
       
        if temp_mittel <= 15:
            
            # Step 1: Überschuss nach Strombedarf
            if pv_ertrag >= strombedarf:
                ueberschuss = pv_ertrag - strombedarf
                eigenverbrauch = strombedarf
            else:
                ueberschuss = 0
                eigenverbrauch = pv_ertrag

            if ueberschuss > 0 and waerme_ps_p < Q_ps:
                heizleistung_neu = heizleistung_max 
                cop_60


            if heizwaermebedarf == 0:
                heizleistung_neu = 0
                waerme_ps = waerme_ps_p - PS_verlust
            elif heizwaermebedarf > heizleistung:
                heizleistung_neu = heizwaermebedarf
                waerme_ps = waerme_ps_p - heizwaermebedarf - PS_verlust + heizleistung_neu
            elif waerme_ps_p > heizwaermebedarf:
                heizleistung_neu = 0
                waerme_ps = waerme_ps_p - heizwaermebedarf - PS_verlust
            elif waerme_ps_p < heizwaermebedarf:
                if Q_ps - waerme_ps_p > heizleistung:
                    heizleistung_neu = heizleistung + Q_ps - waerme_ps_p
                    waerme_ps = waerme_ps_p + heizleistung_neu - heizwaermebedarf - PS_verlust
                else:
                    heizleistung_neu = heizleistung
                    waerme_ps = waerme_ps_p + heizleistung_neu - heizwaermebedarf - PS_verlust
        else:
            # "T_mittel > 15° <- wird nicht geheizt
            heizleistung_neu = 0
            waerme_ps = waerme_ps_p - PS_verlust 

        # Wärmegehalt darf nicht negativ sein
        if waerme_ps <= 0:
            waerme_ps = 0
        
        # Wärmegehalt darf nicht > Q_ps sein

        # Berechnung des Ladezustands
        ladezustand = waerme_ps / Q_ps
        if ladezustand > 1:
            # print("Ladezustand > 1, setze Ladezustand auf 1")
            ladezustand_ps = 1
        elif ladezustand <= 0:
            # print(f"Ladezustand <= 0, setzte 0")
            ladezustand_ps = 0
        else:
            ladezustand_ps = ladezustand

     # Assign calculated values back to the DataFrame
        df.at[time, 'Wärmegehalt PS'] = waerme_ps
        df.at[time, 'Ladezustand PS'] = ladezustand_ps
        df.at[time, 'Heizleistung neu'] = heizleistung_neu
    
    # Handle rows where Heizleistung neu == 0
    df.loc[df['Heizleistung neu'] == 0, 'COP'] = 0
    df['COP'] = df['COP'].replace(0, np.nan).astype(float)

    # Calculate the mean COP for rows where Heizleistung neu > 0
    cop_filtered = df[df['Heizleistung neu'] > 0]['COP']
    COP = round(cop_filtered.mean(),2)

    # Assign elekt. Leistungaufnahme using the full COP column
    df['elekt. Leistungaufnahme'] = (df['Heizleistung neu'] / df['COP']).fillna(0).astype(float)

    # Handle any potential division by zero
    df['elekt. Leistungaufnahme'].fillna(0, inplace=True)

    # Calculate therm. Entnahmelesitung
    df['therm. Entnahmelesitung'] = df['Heizleistung'] - df['elekt. Leistungaufnahme']

    P_el = round(df['elekt. Leistungaufnahme'].sum(), 2)
    return df, P_el, COP


def mit_hems(df, pv):
    # Benutzen den df aus def ohne_pv, also immer muss vorher der laufen

    # df ohne HEMS
    df_ohne = mit_pv(df.copy(), pv)
    
    # pv zu df anpassen und hinzufügen
    pv.index = pv.index.tz_localize(None)
    df.index = df.index.tz_localize(None)
    pv_aligned = pv.reindex(df.index)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # Initialize columns for surplus and WP energy from PV
    df['überschuss'] = 0.0
    df['PV to WP'] = 0.0 # Elektrische Leistung für WP aus PV
    df['eigenverbrauch'] = 0.0 
    df['netzbezug'] = 0.0

    # Iterate through rows
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row['elekt. Leistungaufnahme']  # Electrical power for WP
        pv_to_wp =  0
        ueberschuss = 0
        eigenverbrauch = 0
        netzbezug = 0

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag

        # Step 2: Überschuss für WP (prio)
        if ueberschuss > 0 and p_el_wp > 0:
            if ueberschuss >= p_el_wp:
                pv_to_wp = p_el_wp
                ueberschuss -= p_el_wp
                eigenverbrauch += pv_to_wp
            else:
                pv_to_wp = ueberschuss
                ueberschuss = 0
                eigenverbrauch += pv_to_wp
        else:
            pv_to_wp = 0

        netzbezug = (strombedarf - eigenverbrauch) + (p_el_wp - pv_to_wp)
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0
        
        # Assign values to the DataFrame
        df.at[i, 'überschuss'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
        df.at[i, 'netzbezug'] = netzbezug
    return df, df_ohne
