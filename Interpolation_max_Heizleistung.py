import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

file = './Inputs/max_Heizleistung_NIBE2040-16.csv'  
hz = pd.read_csv(file, index_col = 0)

# hz.index = hz.index.astype(float)  
# hz.columns = hz.columns.astype(float)

def bilinear_interpolate(df):
    # Erstellen einer erweiterten Temperaturreihe
    extended_x = np.arange(-20, 7.5, 0.5)  # Außentemperaturen von -20 bis 15 in Schritten von 0.5
    extended_y = np.arange(35, 55.5, 0.5)    # Wassertemperaturen von 35 bis 55 in Schritten von 0.5
    
    # Extrahieren der bekannten Außentemperaturen (Index) und Wassertemperaturen (Spaltennamen)
    x = df.index.astype(float)  # Außentemperaturen (Index)
    y = df.columns.astype(float)  # Wassertemperaturen (Spalten)

    # Erstellen einer bilinearen Interpolationsfunktion mit RegularGridInterpolator
    interpolator = RegularGridInterpolator((x, y), df.values, method='linear', fill_value=None)

    # Erstellen eines neuen DataFrames mit den erweiterten Temperaturwerten
    extended_df = pd.DataFrame(index=extended_x, columns=extended_y)

    # Interpolierte Werte berechnen und in das DataFrame einfügen
    for i, xi in enumerate(extended_x):
        for j, yi in enumerate(extended_y):
            # Überprüfen, ob der Wert innerhalb des gültigen Bereichs liegt
            # Sicherstellen, dass wir nur Werte innerhalb des ursprünglichen Datenbereichs verwenden
            xi_clipped = np.clip(xi, min(x), max(x))  # Begrenzen der Außentemperatur im Bereich von x
            yi_clipped = np.clip(yi, min(y), max(y))  # Begrenzen der Wassertemperatur im Bereich von y
            
            # Berechnung der interpolierten Werte
            extended_df.iloc[i, j] = interpolator((xi_clipped, yi_clipped)).round(2)  # Interpolation durchführen

    return extended_df

interpolated_df = bilinear_interpolate(hz)
file_name = "inter_max_Heizleistung_NIBE2040-16.csv"  
interpolated_df.to_csv(file_name, index=True)