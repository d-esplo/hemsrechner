import numpy as np
import pandas as pd
import streamlit as st
import heizkurve

def get_waermepumpe(heizlast):
    if heizlast <= 6:
        wp_groesse = 6
        wp = 'Nibe F2040-6'
    elif heizlast <= 8:
        wp_groesse = 8
        wp = 'Nibe F2040-8'
    elif heizlast <= 12:
        wp_groesse = 12
        wp = 'Nibe F2040-12'
    else:
        wp_groesse = 16
        wp = 'Nibe F2040-16'
    return wp_groesse, wp

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
            T_max = 85
        else:
            V_ps = TWL_PR_500
            PS_verlust = 1.4/24 # kWh/24h
            T_max = 95
    elif V_sp_einfach <= VPS_200:
        if V_sp_einfach <= VPS_100:
            V_ps = VPS_100
            PS_verlust = 0.81/24 # kWh/24h
            T_max = 95
        else:
            V_ps= VPS_200
            PS_verlust = 1.4/24 # kWh/24h
            T_max = 95

    # Wärmegehalt Pufferspeicher
    dichte = 1 # kg/m^3
    c_wasser = 4.18 # kJ/(kg·K)
    Q_ps = round(V_ps*dichte*c_wasser*(T_n_vor - T_n_rueck)/3600, 3)

    # Max Wärmegehalt 
    Q_ps_max = round(V_ps*dichte*c_wasser*(T_max - T_n_rueck)/3600, 3)

    # PS überhitzt (mit PV)
    Q_ps_ueber = round(V_ps*dichte*c_wasser*(T_n_vor+5 - T_n_rueck)/3600, 3)

    return V_ps, PS_verlust, Q_ps, Q_ps_max, Q_ps_ueber

def get_max_heizleistung(wp_groesse, df):
    max_hz = pd.read_csv(f'./Inputs/inter_max_Heizleistung_NIBE2040-{wp_groesse}.csv', index_col=0)

    # alles auf float
    max_hz.index = max_hz.index.astype(float)
    max_hz.columns = max_hz.columns.astype(float)

    df['max Heizleistung'] = None

    for i, row in df.iterrows():
        T_aussen = row['T_aussen']
        T_vor = row['T_vor']

        # Nächste-Nachbar-Methode
        if T_aussen not in max_hz.index:
            T_aussen = min(max_hz.index, key=lambda x: abs(x - T_aussen))
        if T_vor not in max_hz.columns:
            T_vor = min(max_hz.columns, key=lambda x: abs(x - T_vor))

        try:
            df.at[i, 'max Heizleistung'] = max_hz.loc[T_aussen, T_vor]
        except KeyError:
            df.at[i, 'max Heizleistung'] = np.nan  

    return df

# Berechnen - immer vorher df aus def ohne_pv erstellen 
def ohne_pv(df, Q_ps, Q_ps_max, PS_verlust):
    ## WP und PS Zusammenfügen
    df['Wärmegehalt PS'] = np.nan
    df['Ladung PS'] = np.nan
    df['Verlust'] = np.nan
    df['Deckung'] = np.nan
    df['Heizleistung WP'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=48, min_periods=1).mean()
    df['wärmebedarf_mittel'] = df['Heizwärmebedarf'].rolling(window=3, min_periods=1).mean()
    df['State'] = 0

    waerme_ps = Q_ps
    ps_30 = Q_ps*0.3
    ps_10 = Q_ps*0.1
    wp = 0

    for i, row in df.iterrows():  # ab der zweiten Zeile
        volllast = row['max Heizleistung']
        teillast = volllast/2
        temp_mittel = row['temp_mittel']
        hzw_mittel = row['wärmebedarf_mittel']
        heizwaermebedarf = row['Heizwärmebedarf']
        lade_ps = 0.0
        state = 0
        verlust = 0
        deckung = 0

        if temp_mittel < 15:
            if hzw_mittel > teillast:
                if waerme_ps - heizwaermebedarf <= ps_10:
                    wp = volllast
                    state = 1
                elif waerme_ps - heizwaermebedarf <= ps_30:
                    wp = teillast
                    state = 2
                else:
                    wp = 0
                    state = 0
            elif 0 < hzw_mittel < teillast:
                if waerme_ps - heizwaermebedarf < ps_30:
                    wp = teillast
                    state = 3
                # elif waerme_ps - heizwaermebedarf < ps_50:
                #     wp = teillast/2
                #     state = 4
                else:
                    wp = 0
                    state = 0
            deckung = heizwaermebedarf - wp - waerme_ps
            lade_ps = wp - PS_verlust - heizwaermebedarf 
            waerme_ps += lade_ps
        else:
            # "T_mittel > 15° <- wird nicht geheizt
            wp = 0
            lade_ps = PS_verlust
            waerme_ps -= lade_ps
            state = 0

        if waerme_ps < 0:
            waerme_ps = 0
        
        if waerme_ps > Q_ps_max:
            verlust = waerme_ps - Q_ps_max
            waerme_ps = Q_ps_max

        if deckung < 0:
            deckung = 0

        df.loc[i, 'Wärmegehalt PS'] = waerme_ps
        df.loc[i, 'Ladung PS'] = lade_ps
        df.loc[i, 'Verlust'] = verlust
        df.loc[i, 'State'] = state
        df.loc[i, 'Heizleistung WP'] = wp
        df.loc[i, 'Deckung'] = deckung

    df.loc[df['Heizleistung WP'] == 0, 'COP'] = np.nan
    df['Strombedarf WP'] = (df['Heizleistung WP'] / df['COP']).fillna(0).astype(float)
    return df

def ohne_pv_alt(df, Q_ps, PS_verlust):
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

    waerme_ps = Q_ps
    V = 300
    d = 1
    c_wasser = 4.18

    for i, row in df.iterrows():  # ab der zweiten Zeile
        max_heizleistung = row['max Heizleistung']
        temp_mittel = row['temp_mittel']
        heizwaermebedarf = row['Heizwärmebedarf']
        heizleistung = row['Heizleistung']
        t_d = row['T_vor'] - row['T_rueck']
        verlust = 0.0
        lade_ps = 0.0
        heizleistung_neu = 0.0
        state = 0.0
        hz = 0.0
        deckung = 0
    
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
    df['einspeisung'] = 0.0
    df['PV to WP'] = 0.0 # Elektrische Leistung für WP aus PV
    df['eigenverbrauch'] = 0.0 
    df['netzbezug'] = 0.0

    # Iterate through rows
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row['Strombedarf WP']  # Electrical power for WP
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
            netzbezug = strombedarf - pv_ertrag

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
        
        # Assign values to the DataFrame
        df.at[i, 'einspeisung'] = float(ueberschuss)
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
    df['einspeisung'] = 0.0
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
        p_el_wp = row.get('Strombedarf WP', 0)  # Electrical power for WP (default 0 if not present)
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
        df.loc[i, 'einspeisung'] = ueberschuss if ueberschuss > 0 else 0.0
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'PV to WP'] = pv_to_wp
        df.loc[i, 'BS to WP'] = bs_to_wp
        df.loc[i, 'battery_soc'] = battery_soc
        df.loc[i, 'BS %'] = battery_soc/battery_capacity
    return df

def mit_pvev(df, pv, homeoffice):
    # Passe Index in PV and Index in df an
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    
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

    df['einspeisung'] = 0.0 
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
        p_el_wp = row['Strombedarf WP']
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
        df.at[i, 'einspeisung'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'PV to EV'] = pv_to_ev
        df.at[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
        df.at[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
    return df

def mit_pvbsev(df, pv, anlage_groesse, battery_capacity, homeoffice):
    # Passe Index in PV and Index in df an
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    
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
    df['einspeisung'] = 0.0
    df['netzbezug'] = 0.0
    df['eigenverbrauch'] = 0.0
    
    # BS Spezifikationen
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity)

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        p_el_wp = row['Strombedarf WP']
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
        df.at[i, 'einspeisung'] = float(ueberschuss)
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
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'BS %'] = battery_soc/battery_capacity
    return df
    
# Ersparnis 
def ersparnis_pv(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(strombedarf + wp_strom, 2)
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
    einspeisung = round(sum(df['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
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
    verbrauch = round(strombedarf+wp_strom, 2)
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
    einspeisung = round(sum(df['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
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
    verbrauch = round(strombedarf + wp_strom + ev_strom, 2)
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
        'stromkosten_ev': stromkosten_ev,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def ersparnis_evbs(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
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
    verbrauch = round(strombedarf + wp_strom + ev_strom, 2)
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
def mit_hems(df, pv, Q_ps, Q_ps_max, Q_ps_ueber, PS_verlust):
    # Ohne HEMS
    df_ohne_pv = ohne_pv(df.copy(), Q_ps, Q_ps_max, PS_verlust)
    df_ohne = mit_pv(df_ohne_pv.copy(), pv)

    # PV 
    # Index für beide anpassen
    pv.index = pv.index.tz_localize(None)
    df.index = df.index.tz_localize(None)
    pv_aligned = pv.reindex(df.index)
    # zu df hinzufugen
    df['PV Ertrag'] = pv_aligned.values.astype(float)
    
    ## WP und PS Zusammenfügen
    df['Heizleistung WP'] = np.nan
    df['Wärmegehalt PS'] = np.nan
    df['Ladung PS'] = np.nan
    df['Verlust'] = np.nan
    df['Deckung'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=48, min_periods=1).mean()
    df['wärmebedarf_mittel'] = df['Heizwärmebedarf'].rolling(window=3, min_periods=1).mean()
    df['State'] = 0.0
    df['einspeisung'] = 0.0
    df['netzbezug'] = 0.0
    df['eigenverbrauch'] = 0.0
    df['PV to WP'] = 0.0

    ps_30 = Q_ps*0.3
    ps_10 = Q_ps*0.1
    wp = 0
    waerme_ps = Q_ps

    for i, row in df.iterrows():  # ab der zweiten Zeile
        # Wärme
        volllast = row['max Heizleistung']
        teillast = volllast/2
        temp_mittel = row['temp_mittel']
        hzw_mittel = row['wärmebedarf_mittel']
        heizwaermebedarf = row['Heizwärmebedarf']
        lade_ps = 0.0
        state = 0
        verlust = 0
        deckung = 0
        
        # Strom
        cop = row['COP']
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ueberschuss = 0
        eigenverbrauch = 0
        pv_to_wp = 0
        strom_wp = 0
        netzbezug = 0

        # Step 1: Überschuss nach Haushaltstrombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - pv_ertrag

        # Step 2: WP 
        # 2.1 State und Überhitzung für SG-Ready 3 vorbereiten
        #     state_2 gibt die Summe der letzte 2 States      
        last_2_states = df['State'].shift(1).rolling(window=2, min_periods=2).sum()
        i_pos = df.index.get_loc(i)  
        if i_pos >= 2:  
            state_2 = last_2_states.iloc[i_pos] 
        else:
            state_2 = 0 
        #     Benötigte Heizleistung für die Überhitzung (+5°C)
        wp_ueber = Q_ps_ueber + heizwaermebedarf - waerme_ps + PS_verlust
        # 2.2 Heizbedarf
        if temp_mittel < 15:
            # SG-Ready 3 möglich?
            if ueberschuss >= 1 and 0 < wp_ueber < volllast and state_2 != 2.2 and hzw_mittel > 0: 
                # Wärme
                wp = wp_ueber
                state = 1.1
            elif hzw_mittel > teillast:
                if waerme_ps - heizwaermebedarf <= ps_10:
                    wp = volllast
                    state = 2
                elif waerme_ps - heizwaermebedarf <= ps_30:
                    wp = teillast
                    state = 3
                else:
                    wp = 0
                    state = 0
            elif 0 < hzw_mittel < teillast:
                if waerme_ps - heizwaermebedarf < ps_30:
                    wp = teillast
                    state = 4
                # elif waerme_ps - heizwaermebedarf < ps_50:
                #     wp = teillast/2
                #     state = 4
                else:
                    wp = 0
                    state = 0
            else:
                wp = 0
                state = 0
            deckung = heizwaermebedarf - wp - waerme_ps
            lade_ps = wp - PS_verlust - heizwaermebedarf 
            waerme_ps += lade_ps
            # Strom
            strom_wp = max(wp / cop, 0)
            pv_to_wp = min(strom_wp, ueberschuss)
            ueberschuss -= pv_to_wp
            eigenverbrauch += pv_to_wp
            netzbezug += strom_wp - pv_to_wp
        else:
            # "T_mittel > 15° <- wird nicht geheizt
            wp = 0
            lade_ps = PS_verlust
            waerme_ps -= lade_ps
            state = 0

        if waerme_ps < 0:
            waerme_ps = 0
        
        if waerme_ps > Q_ps_max:
            verlust = waerme_ps - Q_ps_max
            waerme_ps = Q_ps_max

        if deckung < 0:
            deckung = 0

        ueberschuss = max(0, ueberschuss)
        if ueberschuss > 0 and netzbezug > 0:
            netzbezug_correction = min(netzbezug, ueberschuss)
            netzbezug -= netzbezug_correction
            eigenverbrauch += netzbezug_correction
            ueberschuss -= netzbezug_correction

        df.loc[i, 'Wärmegehalt PS'] = waerme_ps
        df.loc[i, 'Ladung PS'] = lade_ps
        df.loc[i, 'Verlust'] = verlust
        df.loc[i, 'State'] = state
        df.loc[i, 'Heizleistung WP'] = wp
        df.loc[i, 'Deckung'] = deckung
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to WP'] = pv_to_wp
        df.loc[i, 'Strombedarf WP'] = strom_wp

    df.loc[df['Heizleistung WP'] == 0, 'COP'] = np.nan
    return df, df_ohne

def mit_hems_bs(df, df_ohne, pv, battery_capacity, anlage_groesse):
    # def mit_hems zuerst benutzen, dann der df daraus für diese funktion benutzen
    df_ohne = mit_pvbs(df_ohne, pv, anlage_groesse, battery_capacity)
   # Initialize columns for battery and WP calculations
    df['battery_soc'] = 0.0
    df['BS %'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['BS to WP'] = 0.0

    # Battery parameters
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity) n
    
    # Simulation loop
    for i, row in df.iterrows():
        p_el_wp = row['Strombedarf WP'] # Electrical power for WP (default 0 if not present)
        netzbezug = row['netzbezug']
        ueberschuss = row['einspeisung']
        pv_to_wp = row['PV to WP']
        eigenverbrauch = row['eigenverbrauch']
        charge_to_battery = 0
        discharge_from_battery = 0
        bs_to_wp = 0

        # Step 1: Überschuss 2 BS (Prio 3)
        if ueberschuss > 0:
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)
            battery_soc += charge_to_battery
            ueberschuss -= (charge_to_battery / charge_efficiency)
            eigenverbrauch += (charge_to_battery / charge_efficiency)
        else:
            charge_to_battery = 0

        charging_power = c_rate * battery_soc * charge_efficiency  # kW

        # Step 2: Strom von Netz?
        if netzbezug > 0:
            # Entlade Batterie, um Energiemangel zu decken
            discharge_needed = min(netzbezug / discharge_efficiency, charging_power)
            discharge_from_battery = min(discharge_needed, battery_soc - min_soc)
            energy_from_battery = discharge_from_battery * discharge_efficiency
            battery_soc -= discharge_from_battery
            bs_to_wp = p_el_wp - pv_to_wp
            if energy_from_battery >= bs_to_wp:
                bs_to_wp = p_el_wp - pv_to_wp
            else:
                bs_to_wp = 0
            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            remaining_shortfall = netzbezug - energy_from_battery
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
        df.loc[i, 'einspeisung'] = ueberschuss if ueberschuss > 0 else 0.0
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'BS to WP'] = bs_to_wp
        df.loc[i, 'battery_soc'] = battery_soc
        df.loc[i, 'BS %'] = battery_soc/battery_capacity
    
    return df, df_ohne

def mit_hems_ev(df, df_ohne, pv, homeoffice):
    # def mit_hems zuerst benutzen, dann der df daraus für diese funktion benutzen
    df_ohne = mit_pvev(df_ohne, pv, homeoffice)

    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    df['next_day_ev_distanz'] = df.groupby(df.index.date)['ev distanz'].transform('sum').shift(-24)
    
    # EV Spezifikationen
    ev_effizienz = 191 / 1000  # kWh per km
    batteriekapazitaet = 72  # kWh
    batterie_min = 12  # %
    batterie_max = 80  # %
    min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
    max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
    max_ladeleistung = 11  # kW
    ev_soc = max_batterie_niveau
    ev_verbrauch_arbeit = 22*2*ev_effizienz

    df['PV to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0
    df['ev_state'] = 0.0

    for i, row in df.iterrows():
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        next_ev_distanz = row['next_day_ev_distanz'] 
        tag = row.name.dayofweek
        ladeleistung = 0.0
        pv_to_ev = 0.0
        netzbezug = row['netzbezug']
        ueberschuss = row['einspeisung']
        eigenverbrauch = row['eigenverbrauch']
        lade = 0.0
        max_ev_laden = 0.0
        state = 0.0
        next_ev_verbrauch = 0.0
        next_ev_soc = 0.0
        
        # Step 2: EV
        # 2.1: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz * ev_effizienz
            ev_soc = ev_soc - ev_verbrauch

        # 2.2: EV mit PV Laden, wenn zuhause
        if ev_zuhause == 1 and ev_soc < batteriekapazitaet and ueberschuss >= 0.9:
            lade = min(ueberschuss, 11)
            max_ev_laden = batteriekapazitaet - ev_soc
            # Stelle sicher, dass mindestens 1.4 kWh geladen werden
            if lade >= 1.4 and max_ev_laden >= 1.4:
                lade = min(lade, max_ev_laden)
                ev_soc += lade
                ueberschuss -= lade
                pv_to_ev += lade
                eigenverbrauch += lade
                state += 1
            elif 0.9 < ueberschuss < 1.4:
                # Netz unterstutzt mit max. 500 W den Überschussladen
                netzbezug += 1.4 - ueberschuss
                ladeleistung = 1.4
                lade = 0
                ev_soc = min(ev_soc + ladeleistung, batteriekapazitaet)  # Begrenzung
                pv_to_ev += ueberschuss
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
                state += 2
            else:
                lade = 0
        else:
            lade = 0

        # 2.3: Berechne benötigte EV SOC für den nächsten Tag unter der Woche
        if homeoffice:
            if tag in [0, 2] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.1
            else:
                next_ev_soc = 0
        else:
            if tag in [0, 1, 2, 3, 6] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.2
            else:
                next_ev_soc = 0
            
        # 2.4 Berechne benötigte EV SOC für das Wochenende
        next_ev_verbrauch = next_ev_distanz * ev_effizienz
        if tag in [4, 5] and next_ev_verbrauch > ev_soc:
            next_ev_soc = next_ev_verbrauch + min_batterie_niveau
            state += 0.3
        else:
            next_ev_soc = 0

        # 2.5: EV Laden wenn notwendig für den nächsten Tag
        if ev_zuhause == 1 and ev_soc < next_ev_soc:
            ladeleistung = min(11, next_ev_soc - ev_soc)
            state = 0.4
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # 2.6: EV Laden wenn ev_soc < 10%
        if ev_zuhause == 1 and ev_soc < min_batterie_niveau:
            ladeleistung = min(11, min_batterie_niveau - ev_soc)
            state = 0.5
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # Überschuss und Netzbezug noch Mal prüfen
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung + lade
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'ev_state'] = state

    return df, df_ohne

def mit_hems_bsev(df, df_ohne, pv, battery_capacity, anlage_groesse, homeoffice):
    # def mit_hems zuerst benutzen, dann der df daraus für diese funktion benutzen
    df_ohne = mit_pvbsev(df_ohne, pv, anlage_groesse, battery_capacity, homeoffice)

    # BS Parameter
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity) n
    
    # EV Profil
    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    df['next_day_ev_distanz'] = df.groupby(df.index.date)['ev distanz'].transform('sum').shift(-24)
    
    # EV Parameter
    ev_effizienz = 191 / 1000  # kWh per km
    batteriekapazitaet = 72  # kWh
    batterie_min = 12  # %
    batterie_max = 80  # %
    min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
    max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
    max_ladeleistung = 11  # kW
    ev_soc = max_batterie_niveau
    ev_verbrauch_arbeit = 22*2*ev_effizienz

    df['battery_soc'] = 0.0
    df['BS %'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['BS to WP'] = 0.0
    df['PV to EV'] = 0.0
    df['BS to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0
    df['ev_state'] = 0.0

    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']
        pv_ertrag = row['PV Ertrag']
        p_el_wp = row['Strombedarf WP'] # Electrical power for WP (default 0 if not present)
        netzbezug = row['netzbezug']
        ueberschuss = row['einspeisung']
        pv_to_wp = row['PV to WP']
        eigenverbrauch = row['eigenverbrauch']
        charge_to_battery = 0
        discharge_from_battery = 0
        bs_to_wp = 0
        bs_to_ev = 0
        bs_to_str = 0
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        next_ev_distanz = row['next_day_ev_distanz'] 
        tag = row.name.dayofweek
        ladeleistung = 0.0
        pv_to_ev = 0.0
        lade = 0.0
        max_ev_laden = 0.0
        state = 0.0
        next_ev_verbrauch = 0.0
        next_ev_soc = 0.0

        # Step 1: Überschuss 2 BS (Prio 3)
        if ueberschuss > 0:
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)
            battery_soc += charge_to_battery
            ueberschuss -= (charge_to_battery / charge_efficiency)
            eigenverbrauch += (charge_to_battery / charge_efficiency)
        else:
            charge_to_battery = 0

        charging_power = c_rate * battery_soc * charge_efficiency  # kW

        # Step 2: EV
        # 2.1: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz * ev_effizienz
            ev_soc = ev_soc - ev_verbrauch

        # 2.2: EV mit PV Laden, wenn zuhause
        if ev_zuhause == 1 and ev_soc < batteriekapazitaet and ueberschuss >= 0.9:
            lade = min(ueberschuss, 11)
            max_ev_laden = batteriekapazitaet - ev_soc
            # Stelle sicher, dass mindestens 1.4 kWh geladen werden
            if lade >= 1.4 and max_ev_laden >= 1.4:
                lade = min(lade, max_ev_laden)
                ev_soc += lade
                ueberschuss -= lade
                pv_to_ev += lade
                state += 1
            elif 0.9 < ueberschuss < 1.4:
                # Netz unterstutzt mit max. 500 W den Überschussladen
                netzbezug += 1.4 - ueberschuss
                ladeleistung = 1.4
                lade = 0
                ev_soc = min(ev_soc + ladeleistung, batteriekapazitaet)  # Begrenzung
                pv_to_ev += ueberschuss
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
                state += 2
            else:
                lade = 0
        else:
            lade = 0

        # 2.3: Berechne benötigte EV SOC für den nächsten Tag unter der Woche
        if homeoffice:
            if tag in [0, 2] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.1
            else:
                next_ev_soc = 0
        else:
            if tag in [0, 1, 2, 3, 6] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.2
            else:
                next_ev_soc = 0
            
        # 2.4 Berechne benötigte EV SOC für das Wochenende
        next_ev_verbrauch = next_ev_distanz * ev_effizienz
        if tag in [4, 5] and next_ev_verbrauch > ev_soc:
            next_ev_soc = next_ev_verbrauch + min_batterie_niveau
            state += 0.3
        else:
            next_ev_soc = 0

        # 2.5: EV Laden wenn notwendig für den nächsten Tag
        if ev_zuhause == 1 and ev_soc < next_ev_soc:
            ladeleistung = min(max_ladeleistung, next_ev_soc - ev_soc)
            state = 0.4
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # 2.6: EV Laden wenn ev_soc < 10%
        if ev_zuhause == 1 and ev_soc < min_batterie_niveau:
            ladeleistung = min(11, min_batterie_niveau - ev_soc)
            state = 0.5
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # Step 3: Strom von Netz?
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
        df.loc[i, 'einspeisung'] = ueberschuss 
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'BS to Haushalt'] = bs_to_str
        df.loc[i, 'BS to WP'] = bs_to_wp
        df.loc[i, 'BS to EV'] = bs_to_ev
        df.loc[i, 'battery_soc'] = battery_soc
        df.loc[i, 'BS %'] = battery_soc/battery_capacity
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'EV Ladung'] = ladeleistung + lade
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'ev_state'] = state

    return df, df_ohne

# Ersparnis
def ersparnis_hems(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
    wp_strom_ohne = round(sum(df_ohne['Strombedarf WP']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))
    wp_ohne = round(sum(df_ohne['PV to WP']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten - verguetung), 2)
    co2 = round(((netzbezug)*0.380), 2) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    co2_ohne = round(((netzbezug_ohne)*0.380), 2)
    co2_einsparung = round(co2_ohne - co2, 2)

    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'wp ohne': wp_strom_ohne,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbrauch ohne': eigenverbrauch_ohne,
        'PV to WP': wp,
        'PV to WP ohne': wp_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2,
        'co2_ohne': co2_ohne,
        'co2_einsparung': co2_einsparung
    }
    return ergebnisse

def ersparnis_hems_bs(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
    wp_strom_ohne = round(sum(df_ohne['Strombedarf WP']))
    bs = round(sum(df['battery_charge']))
    bs_ohne = round(sum(df_ohne['battery_charge']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))
    wp_ohne = round(sum(df_ohne['PV to WP']))
    bs_to_wp = round(sum(df['BS to WP']))
    bs_to_wp_ohne = round(sum(df_ohne['BS to WP']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten - verguetung), 2)
    co2 = round(((netzbezug)*0.380), 2) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    co2_ohne = round(((netzbezug_ohne)*0.380), 2)
    co2_einsparung = round(co2_ohne - co2, 2)

    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'wp ohne': wp_strom_ohne,
        'bs': bs,
        'bs ohne': bs_ohne,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbrauch ohne': eigenverbrauch_ohne,
        'PV to WP': wp,
        'PV to WP ohne': wp_ohne,
        'BS to WP': bs_to_wp,
        'BS to WP ohne' : bs_to_wp_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2,
        'co2_ohne': co2_ohne,
        'co2_einsparung': co2_einsparung
    }
    return ergebnisse

def ersparnis_hems_ev(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
    wp_strom_ohne = round(sum(df_ohne['Strombedarf WP']))
    ev_strom = round(sum(df['EV Ladung']))
    ev_strom_ohne = round(sum(df_ohne['EV Ladung']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))
    wp_ohne = round(sum(df_ohne['PV to WP']))
    ev = round(sum(df['PV to EV']))
    ev_ohne = round(sum(df_ohne['PV to EV']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten - verguetung), 2)
    co2 = round(((netzbezug)*0.380), 2) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    co2_ohne = round(((netzbezug_ohne)*0.380), 2)
    co2_einsparung = round(co2_ohne - co2, 2)

    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'wp ohne': wp_strom_ohne,
        'ev': ev_strom,
        'ev ohne': ev_strom_ohne,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbrauch ohne': eigenverbrauch_ohne,
        'PV to WP': wp,
        'PV to WP ohne': wp_ohne,
        'PV to EV': ev,
        'PV to EV ohne' : ev_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2,
        'co2_ohne': co2_ohne,
        'co2_einsparung': co2_einsparung
    }
    return ergebnisse
    
def ersparnis_hems_bsev(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['Strombedarf WP']))
    wp_strom_ohne = round(sum(df_ohne['Strombedarf WP']))
    ev_strom = round(sum(df['EV Ladung']))
    ev_strom_ohne = round(sum(df_ohne['EV Ladung']))
    bs = round(sum(df['battery_charge']))
    bs_ohne = round(sum(df_ohne['battery_charge']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im WP
    wp = round(sum(df['PV to WP']))
    wp_ohne = round(sum(df_ohne['PV to WP']))
    ev = round(sum(df['PV to EV']))
    ev_ohne = round(sum(df_ohne['PV to EV']))
    bs_to_wp = round(sum(df['BS to WP']))
    bs_to_wp_ohne = round(sum(df_ohne['BS to WP']))
    bs_to_ev = round(sum(df['BS to EV']))
    bs_to_ev_ohne = round(sum(df_ohne['BS to EV']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten - verguetung), 2)
    co2 = round(((netzbezug)*0.380), 2) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    co2_ohne = round(((netzbezug_ohne)*0.380), 2)
    co2_einsparung = round(co2_ohne - co2, 2)

    ergebnisse = {
        'strombedarf': strombedarf,
        'wp': wp_strom,
        'wp ohne': wp_strom_ohne,
        'ev': ev_strom,
        'ev ohne': ev_strom_ohne,
        'bs': bs,
        'bs ohne': bs_ohne,
        'pv': pv,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbrauch ohne': eigenverbrauch_ohne,
        'PV to WP': wp,
        'PV to WP ohne': wp_ohne,
        'PV to EV': ev,
        'PV to EV ohne' : ev_ohne,
        'BS to WP': bs_to_wp,
        'BS to WP ohne' : bs_to_wp_ohne,
        'BS to EV': bs_to_ev,
        'BS to EV ohne' : bs_to_ev_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2,
        'co2_ohne': co2_ohne,
        'co2_einsparung': co2_einsparung
    }
    return ergebnisse

# Print
def print_ersparnis_hems(ergebnisse):
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            print(f"{label}: {ergebnisse[key]}")

    print_if_available('Haushaltsstrombedarf in kWh', 'strombedarf')
    print_if_available('Jahresertrag in kWh', 'pv')
    print('')  # Leere Zeile zur Trennung
    print('Ohne HEMS')  
    print_if_available('Wärmepumpe Strombedarf in kWh', 'wp ohne')
    print_if_available('EV Strombedarf in kWh', 'ev ohne')
    print('')
    print_if_available('Geladene PV-Strom in Wärmepumpe in kWh', 'PV to WP ohne')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'bs ohne')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV ohne')
    print('')
    print_if_available('Geladene BS-Strom in Wärmepumpe in kWh', 'BS to WP ohne')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV ohne')
    print('')
    print_if_available('Netzbezug in kWh', 'netzbezug ohne')
    print_if_available('Stromkosten in €/a', 'stromkosten ohne')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung ohne')
    print_if_available('Einspeisevergütung in €/a', 'verguetung ohne')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch ohne')
    print_if_available('kg CO₂/a', 'co2_ohne')
    print('')
    print('Mit HEMS') 
    print_if_available('Wärmepumpe Strombedarf in kWh', 'wp')
    print_if_available('EV Strombedarf in kWh', 'ev')
    print('')
    print_if_available('Geladene PV-Strom in Wärmepumpe in kWh', 'PV to WP')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'bs')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV')
    print('')
    print_if_available('Geladene BS-Strom in Wärmepumpe in kWh', 'BS to WP')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV')
    print('')
    print_if_available('Netzbezug in kWh', 'netzbezug')
    print_if_available('Stromkosten in €/a', 'stromkosten')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung')
    print_if_available('Einspeisevergütung in €/a', 'verguetung')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch')
    print_if_available('kg CO₂/a', 'co2')
    print('')  
    print_if_available('Stromkosten Einsparung in €/a', 'einsparung')
    print_if_available('CO2 Einsparung kg CO₂/a', 'co2_einsparung')

def print_ersparnis_hems_st(ergebnisse):
     # Helper-Funktion: nur vorhandene Schlüssel anzeigen
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            st.write(f"- {label}: {ergebnisse[key]}")
    
    st.subheader("Ergebnisse", divider=True)
    row1 = st.columns(3)  # Erste Zeile: 3 Spalten
    row2 = st.columns(3)  # Zweite Zeile: 3 Spalten

    with row1[0]:
        with st.container(border=True):
            st.write('##### Strombedarf [kWh]')
            print_if_available('Haushalt', 'strombedarf')
            print_if_available('WP', 'wp')
            print_if_available('EV', 'ev')
    
    with row1[1]:
        with st.container(border=True):
            st.write("##### PV [kWh]")
            print_if_available('Jahresertrag', 'pv')
            print_if_available('Eigenverbrauch', 'eigenverbrauch')
            print_if_available('PV to WP', 'PV to WP')
            print_if_available('PV to BS', 'bs')
            print_if_available('PV to EV', 'PV to EV')

    with row1[2]:
        with st.container(border=True):
            st.write("##### BS [kWh]")
            print_if_available('PV to BS', 'bs')
            print_if_available('BS to WP', 'BS to WP')
            print_if_available('BS to EV', 'BS to EV')

    with row2[0]:
        with st.container(border=True):
            st.write("##### Ohne HEMS")
            print_if_available('Einspeisung [kWh]', 'einspeisung ohne')
            print_if_available('Einspeisevergütung [€/a]', 'verguetung ohne')
            print_if_available('Netzbezug [kWh]', 'netzbezug ohne')
            print_if_available('Stromkosten [€/a]', 'stromkosten ohne')
            print_if_available('CO₂-Emissionen [kg CO₂/a]', 'co2_ohne')

    with row2[1]:
        with st.container(border=True):
            st.write("##### Mit HEMS")
            print_if_available('Einspeisung [kWh]', 'einspeisung')
            print_if_available('Einspeisevergütung [€/a]', 'verguetung')
            print_if_available('Netzbezug [kWh]', 'netzbezug')
            print_if_available('Stromkosten [€/a]', 'stromkosten')
            print_if_available('Stromkosten [€/a]', 'stromkosten_bs')
            print_if_available('CO₂-Emissionen [kg CO₂/a]', 'co2')

    with row2[2]:
            with st.container(border=True):
                st.write("##### Einsparung [€/a]")
                print_if_available('mit HEMS [€/a]', 'einsparung')
                print_if_available('mit HEMS [kg CO₂/a]', 'co2_einsparung')