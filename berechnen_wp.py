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

def ohne_pv(lastprofil_h, Q_ps, PS_verlust):
    ## WP und PS Zusammenfügen
    df = lastprofil_h
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
    df['Surplus'] = 0.0
    df['WP P_el from PV'] = 0.0

    # Iterate through rows
    for i, row in df.iterrows():
        strombedarf = row['Strombedarf']  # Strombedarf at current time
        pv_ertrag = row['PV Ertrag']  # PV generation at current time
        p_el_wp = row['elekt. Leistungaufnahme']  # Electrical power for WP

        # Calculate surplus after covering Strombedarf
        if pv_ertrag >= strombedarf:
            surplus = pv_ertrag - strombedarf  # Remaining PV energy
            # Check if surplus can cover P_el for the WP
            if surplus >= p_el_wp and p_el_wp > 0:
                wp_p_el_from_pv = p_el_wp
                surplus -= p_el_wp
            elif p_el_wp > 0:
                wp_p_el_from_pv = surplus
                surplus = 0
        else:
            surplus = 0
            wp_p_el_from_pv = 0
        
        # Assign values to the DataFrame
        df.at[i, 'Surplus'] = float(surplus)
        df.at[i, 'WP P_el from PV'] = float(wp_p_el_from_pv)
    return df

def kosten(df, strompreis):
    if 'elekt. Leistungaufnahme' not in df.columns:
        print("Error: Column 'elekt. Leistungaufnahme' is missing!")
        print("Available columns:", df.columns)

    kosten_ohne = df['elekt. Leistungaufnahme']*strompreis
    kosten_ohne = round(kosten_ohne.sum(), 2)
    kosten_mit = (df['elekt. Leistungaufnahme'] - df['WP P_el from PV'])*strompreis
    kosten_mit = round(kosten_mit.sum(), 2)
    ersparnis = round(kosten_ohne - kosten_mit, 2)
    return kosten_ohne, kosten_mit, ersparnis

