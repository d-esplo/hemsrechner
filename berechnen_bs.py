import pandas as pd
import streamlit as st

def mit_pv(df, pv, anlage_groesse, battery_capacity):
    pv.index = pv.index.tz_localize(None)
    df.index = df.index.tz_localize(None)
    pv_aligned = pv.reindex(df.index)
    # zu df hinzufugen
    df['PV Ertrag'] = pv_aligned.values.astype(float)
    
    # Battery parameters
    c_rate = 1
    charge_efficiency = 0.96  # BYD HVS & HVM
    discharge_efficiency = 0.96
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 0.5*battery_capacity  # Initial state of charge in kWh (50% of battery capacity)

    if anlage_groesse<battery_capacity:
        battery_capacity = anlage_groesse

    # Adding columns to the DataFrame for the simulation results
    df['battery_soc'] = 0.0
    df['soc %'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['netzeinspeisung'] = 0.0
    df['überschuss'] = 0.0
    df['netzbezug'] = 0.0
    df['eigenverbrauch'] = 0.0

    # Simulation loop
    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']

        if pv_ertrag >= strombedarf:
            # Surplus PV production
            ueberschuss = pv_ertrag - strombedarf

            # Charge the battery with the surplus, limited by the charging power and max_soc
            charge_potential = ueberschuss * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)

            # Update battery state of charge
            battery_soc += charge_to_battery 

            # Calculate excess PV after charging battery
            ueberschuss = ueberschuss - (charge_to_battery / charge_efficiency)

            # Energy to be exported to the grid
            grid_export = ueberschuss

            # Update DataFrame
            df.loc[i, 'battery_charge'] = charge_to_battery
            df.loc[i, 'netzeinspeisung'] = grid_export if grid_export > 0 else 0.0
            df.loc[i, 'netzbezug'] = 0.0  # No grid import in surplus case
            df.loc[i, 'eigenverbrauch'] = strombedarf

        elif strombedarf > 0:
            charging_power = c_rate * battery_soc * charge_efficiency
            # PV production is less than AC consumption
            shortfall = strombedarf - pv_ertrag
            # Discharge battery to meet the shortfall, limited by discharging power and min_soc
            discharge_needed = min(shortfall / discharge_efficiency, charging_power)
            discharge_from_battery = min(discharge_needed, battery_soc-min_soc)

            # Actual energy supplied to AC from battery
            energy_from_battery = discharge_from_battery * discharge_efficiency

        
            # Update battery state of charge
            battery_soc -= discharge_from_battery
        
            # Calculate any remaining shortfall after battery discharge
            remaining_shortfall = shortfall - energy_from_battery

            # Energy imported from the grid to cover the remaining shortfall
            grid_import = remaining_shortfall if remaining_shortfall > 0 else 0.0

            # Update DataFrame
            df.loc[i, 'battery_discharge'] = discharge_from_battery
            df.loc[i, 'netzbezug'] = grid_import
            df.loc[i, 'netzeinspeisung'] = 0.0  # No grid export in deficit case
            df.loc[i, 'eigenverbrauch'] = energy_from_battery + pv_ertrag

        # Update SOC in the DataFrame
        df.loc[i, 'battery_soc'] = battery_soc
        df.loc[i, 'soc %'] = battery_soc/battery_capacity
        
    # Optional: Set battery_soc to not exceed capacity or drop below 0
    # df['battery_soc'] = df['battery_soc'].clip(lower=min_soc, upper=max_soc)
    return df

def ersparnis(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['netzeinspeisung']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher 
    batterie = round(sum(df['battery_charge']))

    # Direkter Verbrauch an PV-Strom
    pv_direkt = eigenverbrauch - batterie

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    strombedarf = round(sum(df['Strombedarf']), 2)
    stromkosten_ohne_pv = round(strombedarf * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten - verguetung), 2)

    # CO2
    co2_ohne = strombedarf*0.38
    co2 = netzbezug*0.38
    co2_einsparung = round(co2_ohne - co2)
    
    ergebnisse = {
    'pv': pv,
    'strombedarf' : strombedarf,
    'eigenverbrauch': eigenverbrauch,
    'batterie': batterie,
    'pv_direkt': pv_direkt,
    'netzbezug': netzbezug,
    'einspeisung': einspeisung,
    'stromkosten_ohne_pv': stromkosten_ohne_pv,
    'stromkosten': stromkosten,
    'verguetung': verguetung,
    'einsparung': einsparung,
    'co2 einsparung': co2_einsparung
    }
    return ergebnisse

def print_ersparnis(ergebnisse):
    # Print
    print('Jahresertrag in kWh: ', ergebnisse.get('pv'))
    print('Eigenverbrauch in kWh: ', ergebnisse.get('eigenverbrauch'))
    print('Geladene PV-Strom in Batteriespeicher in kWh: ', ergebnisse.get('batterie'))
    print('')
    print('Netzbezug in kWh: ', ergebnisse.get('netzbezug'))
    print('Einspeisung ins Netz in kWh: ', ergebnisse.get('einspeisung'))
    print('')
    print('Stromkosten ohne PV in €/a: ', ergebnisse.get('stromkosten_ohne_pv'))
    print('Stromkosten mit PV & BS in €/a: ', ergebnisse.get('stromkosten'))
    print('Einspeisevergütung in €/a: ', ergebnisse.get('verguetung'))
    print('Stromkosten Einsparung in €/a: ', ergebnisse.get('einsparung'))

def print_ersparnis_st(ergebnisse):
    st.subheader("Ergebnisse", divider=True)
    def print_if_available(label, key):
            if key in ergebnisse and ergebnisse[key] is not None:
                st.write(f"- {label}: {ergebnisse[key]}")
    
    row1 = st.columns(2)  # Erste Zeile: 2 Spalten
    row2 = st.columns(2)  # Zweite Zeile: 2 Spalten
    row3 = st.columns(1)

    with row1[0]:
        with st.container(border=True):
            st.write('##### Strombedarf [kWh]')
            print_if_available('Haushalt', 'strombedarf')
    
    with row1[1]:
        with st.container(border=True):
            st.write("##### PV [kWh]")
            print_if_available('Jahresertrag', 'pv')
            print_if_available('Eigenverbrauch', 'eigenverbrauch')
            print_if_available('PV to BS', 'batterie')

    with row2[0]:
        with st.container(border=True):
            st.write("##### Ohne PV + BS")
            print_if_available('Netzbezug [kWh]', 'strombedarf')
            print_if_available('Stromkosten [€/a]', 'stromkosten_ohne_pv')

    with row2[1]:
        with st.container(border=True):
            st.write("##### Mit PV + BS")
            print_if_available('Netzbezug [kWh]', 'netzbezug')
            print_if_available('Einspeisung [kWh]', 'einspeisung')
            print_if_available('Einspeisevergütung [€/a]', 'verguetung')
            print_if_available('Stromkosten [€/a]', 'stromkosten')

    with row3[0]:
            with st.container(border=True):
                st.write("##### Einsparung [€/a]")
                print_if_available('mit PV + BS [€/a]', 'einsparung')
                print_if_available('mit PV + BS [kg CO₂/a]', 'co2 einsparung')

   
