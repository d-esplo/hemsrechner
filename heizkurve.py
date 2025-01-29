import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
from scipy.spatial import KDTree, cKDTree

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

    heizkurve = pd.DataFrame()
    heizkurve['T_aussen'] = T_aussen
    heizkurve['Lastverhältnis'] = np.divide(T_soll-heizkurve['T_aussen'], T_soll-T_n_aussen)
    heizkurve['e^x'] = np.exp(np.divide((heizkurve['Lastverhältnis']**(p-1/p))*(T_n_vor-T_n_rueck), T_m_n_ueber))
    heizkurve['T_vor'] = np.divide(heizkurve['e^x']*((T_n_vor-T_n_rueck)*heizkurve['Lastverhältnis']+T_soll)-T_soll, heizkurve['e^x']-1)
    heizkurve['T_rueck'] = heizkurve['T_vor']-heizkurve['Lastverhältnis']*(T_n_vor-T_n_rueck)
    return heizkurve, T_soll, T_n_vor, T_n_rueck

def plot_heizkurve(heizkurve):
    plt.plot(heizkurve['T_aussen'], heizkurve['T_vor'], label = 'Vorlauftempeteratur')
    plt.plot(heizkurve['T_aussen'], heizkurve['T_rueck'], label = 'Rücklauftemperatur')
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
    heizleistung_auslegung = pd.DataFrame({
        'T_aussen': index,
        'Lastverhältnis': lastverhaeltnis,
        'Heizleistung Auslegung': heizwaerme_auslegung,
        'Heizleistung Theoretisch': heizwaerme_theoretisch
    }, index=index)
    # hier enthalten index und Spalte T_aussen die T_aussen
    return heizleistung_auslegung

def plot_heizleistung(heizleistung_auslegung):
    # Heizleistung in Abhängigkeit der Außentemperatur
    plt.plot(heizleistung_auslegung['Heizleistung Auslegung'], label = 'Heizleistung Auslegung [kW]')
    plt.plot(heizleistung_auslegung['Heizleistung Theoretisch'], label = 'Heizleistung Theoretisch [kW]')

    plt.xlabel('Außentemperatur [°C]')
    plt.ylabel('Heizleistung [kW]')
    plt.title('Heizleistung in Abhängigkeit der Außentemperatur')
    plt.grid(True)
    plt.legend()
    plt.show()
    return plt

def get_heizleistung_profil(df, heizleistung_auslegung):
    # Ensure T_aussen is numeric
    heizleistung_auslegung = heizleistung_auslegung.sort_values('T_aussen')
    tree = KDTree(heizleistung_auslegung['T_aussen'].values.reshape(-1, 1))

    # Find the nearest neighbors
    distances, indices = tree.query(df['T_aussen'].values.reshape(-1, 1))
    df['Heizleistung'] = heizleistung_auslegung.iloc[indices]['Heizleistung Auslegung'].values
    return df

def get_cop(wp_groesse, df):
    # Load the COP table
    COP = pd.read_csv(f'./Inputs/COP_Nibe F2040-{wp_groesse}_regression.csv', index_col=0)

    # Ensure index and columns are floats
    COP.index = COP.index.astype(float)
    COP.columns = COP.columns.astype(float)

    df['COP'] = None
    df['COP_60'] = None
    df['COP_40'] = None

    for i, row in df.iterrows():
        T_aussen = row['T_aussen']
        T_vor = row['T_vor']

        # Check for nearest values
        if T_aussen not in COP.index:
            T_aussen = min(COP.index, key=lambda x: abs(x - T_aussen))
        if T_vor not in COP.columns:
            T_vor = min(COP.columns, key=lambda x: abs(x - T_vor))

        try:
            df.at[i, 'COP'] = COP.loc[T_aussen, T_vor]
            df.at[i, 'COP_60'] = COP.loc[T_aussen, 60]
            df.at[i, 'COP_40'] = COP.loc[T_aussen, 40]
        except KeyError:
            df.at[i, 'COP'] = np.nan  # Handle missing data gracefully

    return df
