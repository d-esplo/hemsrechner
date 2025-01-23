import numpy as np
import pandas as pd

def get_waermepumpe(heizlast):
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
    return wp_groesse

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

def ohne_pv(df, Q_ps, PS_verlust):
    ## WP und PS Zusammenfügen
    df['Wärmegehalt PS'] = np.nan
    df['Ladezustand PS'] = np.nan
    df['Heizleistung neu'] = np.nan
    df['temp_mittel'] = df['T_aussen'].rolling(window=48, min_periods=1).mean()
    df['Wärmebedarf_mittel'] = df['Heizwärmebedarf'].rolling(window=48, min_periods=1).mean()

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
       
        if temp_mittel <= 15: 
            if heizwaermebedarf == 0:
                heizleistung_neu = 0
                waerme_ps = waerme_ps_p - heizwaermebedarf - PS_verlust
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

def mit_pv(df, pv):
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

    # Iterate through rows
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row['elekt. Leistungaufnahme']  # Electrical power for WP

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
        
        # Assign values to the DataFrame
        df.at[i, 'überschuss'] = float(ueberschuss)
        df.at[i, 'PV to WP'] = float(pv_to_wp)
        df.at[i, 'eigenverbrauch'] = float(eigenverbrauch)
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

    # Battery parameters
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity)

    if anlage_groesse<battery_capacity:
        battery_capacity = anlage_groesse
    
    charging_power = c_rate * battery_capacity * charge_efficiency  # kW

    # Simulation loop
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row.get('elekt. Leistungaufnahme', 0)  # Electrical power for WP (default 0 if not present)

         # Step 1: Überschuss 2 Strombedarf (Prio 1)
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag

        # Step 2: Überschuss 2 WP (Prio 2)
        if ueberschuss >= p_el_wp:
            ueberschuss -= p_el_wp
            eigenverbrauch += p_el_wp 
            pv_to_wp = eigenverbrauch if p_el_wp > 0 else 0.0
        else:
            pv_to_wp = ueberschuss 
            ueberschuss = 0

        # Step 3: Überschuss 2 BS (Prio 3)
        if ueberschuss > 0:
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)
            battery_soc += charge_to_battery
            ueberschuss -= (charge_to_battery / charge_efficiency)
            eigenverbrauch += charge_to_battery
        else:
            charge_to_battery = 0

        # Step 5: Strom von Netz?
        energiemangel = strombedarf + p_el_wp - pv_ertrag
        if energiemangel > 0:
            # Entlade Batterie, um Energiemangel zu decken
            discharge_needed = min(energiemangel / discharge_efficiency, charging_power)
            discharge_from_battery = min(discharge_needed, battery_soc - min_soc)
            energy_from_battery = discharge_from_battery * discharge_efficiency
            battery_soc -= discharge_from_battery

            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            remaining_shortfall = energiemangel - energy_from_battery
            netzbezug = max(remaining_shortfall, 0)
        else:
            discharge_from_battery = 0
            netzbezug = 0

        # Update DataFrame
        df.loc[i, 'battery_charge'] = charge_to_battery
        df.loc[i, 'battery_discharge'] = discharge_from_battery
        df.loc[i, 'überschuss'] = ueberschuss if ueberschuss > 0 else 0.0
        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'PV to WP'] = pv_to_wp
        df.loc[i, 'battery_soc'] = battery_soc
    return df

def ersparnis_bs(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    wp_strom = round(sum(df['elekt. Leistungaufnahme']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    batterie = round(sum(df['battery_charge']))
    wp = round(sum(df['PV to WP']))

    # Direkter Verbrauch an PV-Strom
    pv_direkt = eigenverbrauch - batterie

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
        'batterie': batterie,
        'PV to WP': wp,
        'pv_direkt': pv_direkt,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def print_ersparnis(ergebnisse):
    # Print
    print('Haushaltsstrombedarf in kWh: ', ergebnisse.get('strombedarf'))
    print('Wärmepumpe Strombedarf in kWh: ', ergebnisse.get('wp'))
    print('Jahresertrag in kWh: ', ergebnisse.get('pv'))
    print('Eigenverbrauch in kWh: ', ergebnisse.get('eigenverbrauch'))
    print('Geladene PV-Strom in Batteriespeicher in kWh: ', ergebnisse.get('batterie'))
    print('Geladene PV-Strom in Wärmepumpe in kWh: ', ergebnisse.get('PV to WP'))
    print('Direkter Verbrauch PV-Strom in kWh: ', ergebnisse.get('pv_direkt'))
    print('')
    print('Netzbezug in kWh: ', ergebnisse.get('netzbezug'))
    print('Einspeisung ins Netz in kWh: ', ergebnisse.get('einspeisung'))
    print('')
    print('Stromkosten ohne PV in €/a: ', ergebnisse.get('stromkosten_ohne_pv'))
    print('Stromkosten mit PV & BS in €/a: ', ergebnisse.get('stromkosten'))
    print('Einspeisevergütung in €/a: ', ergebnisse.get('verguetung'))
    print('Stromkosten Einsparung in €/a: ', ergebnisse.get('einsparung'))

