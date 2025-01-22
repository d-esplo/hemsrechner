import pandas as pd

# def get_batteriespeicher():
#     return

def mit_pv(df, pv, battery_capacity):
    # Remove timezone information from `pv`
    pv.index = pv.index.tz_localize(None)

    # Ensure `df` index is datetime
    df.index = pd.to_datetime(df.index)

    # Align `pv` with `df` by reindexing and filling any missing values
    pv_aligned = pv.reindex(df.index).fillna(0)

    # Add PV data to the DataFrame
    df['PV Ertrag'] = pv_aligned.values.astype(float)
    
    # Battery parameters
    c_rate = 1
    charge_efficiency = 0.96 # BYD HVS & HVM
    discharge_efficiency = 0.96
    charging_power = c_rate * battery_capacity * charge_efficiency # kW
    min_soc = 1
    max_soc = battery_capacity
    battery_soc = 5  # Initial state of charge in kWh (50% of battery capacity)

    # Adding columns to the DataFrame for the simulation results
    df['battery_soc'] = 0.0
    df['battery_charge'] = 0.0
    df['battery_discharge'] = 0.0
    df['grid_export'] = 0.0
    df['pv_excess'] = 0.0
    df['grid_import'] = 0.0
    df['eigenverbrauch'] = 0.0

    # Simulation loop
    for i, row in df.iterrows():
        pv_production = row['PV Ertrag']
        ac_consumption = row['Strombedarf']

        if pv_production >= ac_consumption:
            # Surplus PV production
            surplus = pv_production - ac_consumption

            # Charge the battery with the surplus, limited by the charging power and max_soc
            charge_potential = surplus * charge_efficiency
            charge_to_battery = min(charge_potential, max_soc - battery_soc)

            # Update battery state of charge
            battery_soc += charge_to_battery

            # Calculate excess PV after charging battery
            pv_excess = surplus - (charge_to_battery / charge_efficiency)

            # Energy to be exported to the grid
            grid_export = pv_excess

            # Update DataFrame
            df.loc[i, 'battery_charge'] = charge_to_battery
            df.loc[i, 'grid_export'] = grid_export
            df.loc[i, 'pv_excess'] = pv_excess
            df.loc[i, 'grid_import'] = 0.0  # No grid import in surplus case
            df.loc[i, 'eigenverbrauch'] = ac_consumption

        else:
            # PV production is less than AC consumption
            shortfall = ac_consumption - pv_production

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
            df.loc[i, 'grid_import'] = grid_import
            df.loc[i, 'grid_export'] = 0.0  # No grid export in deficit case
            df.loc[i, 'pv_excess'] = 0.0  # No excess PV in deficit case
            df.loc[i, 'eigenverbrauch'] = energy_from_battery + pv_production

        # Update SOC in the DataFrame
        df.loc[i, 'battery_soc'] = battery_soc
    # Optional: Set battery_soc to not exceed capacity or drop below 0
    # df['battery_soc'] = df['battery_soc'].clip(lower=min_soc, upper=max_soc)
    return df

def ersparnis(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['grid_import']))
    einspeisung = round(sum(df['grid_export']))

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
    verbrauch = round(sum(df['Strombedarf']), 2)
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
    'pv': pv,
    'eigenverbrauch': eigenverbrauch,
    'batterie': batterie,
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
    print('Jahresertrag in kWh: ', ergebnisse.get('pv'))
    print('Eigenverbrauch in kWh: ', ergebnisse.get('eigenverbrauch'))
    print('Geladene PV-Strom in Batteriespeicher in kWh: ', ergebnisse.get('batterie'))
    print('Direkter Verbrauch PV-Strom in kWh: ', ergebnisse.get('pv_direkt'))
    print('')
    print('Netzbezug in kWh: ', ergebnisse.get('netzbezug'))
    print('Einspeisung ins Netz in kWh: ', ergebnisse.get('einspeisung'))
    print('')
    print('Stromkosten ohne PV in €/a: ', ergebnisse.get('stromkosten_ohne_pv'))
    print('Stromkosten mit PV & BS in €/a: ', ergebnisse.get('stromkosten'))
    print('Einspeisevergütung in €/a: ', ergebnisse.get('verguetung'))
    print('Stromkosten Einsparung in €/a: ', ergebnisse.get('einsparung'))

