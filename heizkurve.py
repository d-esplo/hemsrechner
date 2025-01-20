import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 

def get_heizkurve(heizung, T_aussen, T_n_aussen):
    ## Die Heizkurve beschreibt den Zusammenhang zwischen Außentemperatur und Vorlauftemperatur. 
    ## Sie wird zur Regelung der Vorlauftemperatur der Heizungsanlage genutzt.
    # Berechnung nach “Heße - 2020 - Energieeffiziente Wärmeversorgung von Gebäuden Tatsächliche Versorgungsverhältnisse und Maßnahmen”
    
    # T_n_vor, T_n_rueck definieren
    if heizung == 'Fußbodenheizung':
        T_n_vor = 35
        T_n_rueck = 28
        T_soll = 20
        p = 1.1
        T_m_n_ueber = (T_n_vor-T_n_rueck)/(np.log((T_n_vor-T_soll)/(T_n_rueck-T_soll)))
    else:
        T_n_vor = 55
        T_n_rueck = 45
        T_soll = 20
        p = 1.3
        T_m_n_ueber = (T_n_vor-T_n_rueck)/(np.log((T_n_vor-T_soll)/(T_n_rueck-T_soll)))

    heizkurve = pd.DataFrame
    heizkurve['T_aussen'] = T_aussen
    heizkurve['Lastverhältnis'] = np.divide(T_soll-heizkurve['temp'], T_soll-T_n_aussen)
    heizkurve['e^x'] = np.exp(np.divide((heizkurve['Lastverhältnis']**(p-1/p))*(T_n_vor-T_n_rueck), T_m_n_ueber))
    heizkurve['T_vor'] = np.divide(heizkurve['e^x']*((T_n_vor-T_n_rueck)*heizkurve['Lastverhältnis']+T_soll)-T_soll, heizkurve['e^x']-1)
    heizkurve['T_rueck'] = heizkurve['T_vor']-heizkurve['Lastverhältnis']*(T_n_vor-T_n_rueck)
    return heizkurve, T_soll, T_n_vor, T_n_rueck

def plot_heizkurve(heizkurve):
    plt.plot(heizkurve['temp'], heizkurve['T_vor'], label = 'Vorlauftempeteratur')
    plt.plot(heizkurve['temp'], heizkurve['T_rueck'], label = 'Rücklauftemperatur')
    plt.xlabel('Außentemperatur [°C]')
    plt.ylabel('T_vorlauf/T_ruecklauf [°C]')
    plt.title('Heizkurve')
    plt.grid(True)
    plt.legend()
    plt.show()
    return plt

def get_heizleistung(T_n_aussen, wp_groesse, T_soll):
    # Berechnet Heizleistung Auslegung und Heizleistung Theoretisch
    T_aussen_end = 15  # Endwert der Temperatur
    step = 0.1  # Schrittweite

    # Index erstellen
    index = np.arange(T_n_aussen, T_aussen_end + step, step)

    # Heizwärme Auslegung berechnen
    length = len(index)
    heizwaerme_auslegung = wp_groesse - (np.arange(length) / (length - 1)) * wp_groesse
    lastverhaeltnis = np.divide(T_soll-index, T_soll-T_n_aussen)
    heizwaerme_theoretisch = lastverhaeltnis*wp_groesse

    # DataFrame erstellen
    auslegungs_heizleistung = pd.DataFrame({
        'T_aussen': index,
        'Lastverhältnis': lastverhaeltnis,
        'Heizleistung Auslegung': heizwaerme_auslegung,
        'Heizleistung Theoretisch': heizwaerme_theoretisch
    }, index=index)

    # T_aussen-Spalte entfernen, da diese im Index enthalten ist
    auslegungs_heizleistung.drop(columns='T_aussen', inplace=True)
    return auslegungs_heizleistung

def get_cop(wp_groesse, T_aussen_df, T_vor_df):
    # COP Tabelle einlesen
    COP = pd.read_csv(pd.read_csv(f'./Inputs/COP_Nibe F2040-{wp_groesse}.csv'))

    # Initialize the result list for COPs
    df = pd.DataFrame
    df['T_aussen'] = T_aussen_df
    df['T_vor'] = T_vor_df
    df['COP'] = None

    # Iterate over rows in t_amb to find the closest COP for each row
    for i, row in df.iterrows():
        T_aussen = row['T_aussen']
        T_vor = row['T_vor']
        
        # Initialize variables to find the closest point
        naechster_cop = None
        kleinster_abstand = float('inf')  # Start with an infinitely large distance
        
        # Iterate over interpolated_df index (ambient temp) and columns (water temp)
        for x in COP.index:
            for y in COP.columns:
                abstand = abs(x - T_aussen) + abs(y - T_vor)  # Combined distance
                
                # Update if the current distance is the smallest
                if abstand < kleinster_abstand:
                    kleinster_abstand = abstand
                    naechster_cop = COP.loc[x, y]
        
        # Assign the closest COP value to the current row
        df.at[i, 'COP'] = naechster_cop
    return df['COP']
