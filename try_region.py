import pandas as pd

def get_try_t_n_aussen(plz):
    ## TRY Region und T_n_aussen
    # Norm-Außentemperatur/Auslegungsaußentemperatur aus DIN/TS 12831-1
    klimadaten = pd.read_excel('./Inputs/Klimadaten.xlsx')

    naechste_plz = None
    kleinster_abstand = float('inf')  # Setze den anfänglichen Abstand auf unendlich
    T_n_aussen = None

    for index, row in klimadaten.iterrows():
        abstand = abs(row['PLZ'] - plz)  # Absoluter Unterschied zwischen PLZ
        if abstand < kleinster_abstand:  # Prüfen, ob der aktuelle Abstand kleiner ist
            kleinster_abstand = abstand
            naechste_plz = row['PLZ']
            T_n_aussen = row['Auslegungsaußentemperatur']
            TRY_region = row['TRY']

    return TRY_region, T_n_aussen