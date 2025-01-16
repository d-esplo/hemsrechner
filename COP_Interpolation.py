import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

# COP INTERPOLATION

# Nibe F2040 -> Teschnische Daten https://assetstore.nibe.se/hcms/v2.3/entity/document/24898/storage/MDI0ODk4LzAvbWFzdGVy
# COP bei Verschiedene Vorlauftemperaturen S. 67-68
# Nominelle Heizleistung bei europäisches Durchnittsklima S. 70

# COP Dictionary für Nibe F2024 6 bis 16
COP_6 = pd.DataFrame({'35':[1.5, 2.3, 2.5, 2.6, 2.6, 3.3, 3.6], 
                    '45':[1.6, 1.8, 2, 2.2, 2.3, 2.9, 3.3], 
                    '55':[1.4, 1.6, 1.7, 1.9, 2.1, 2.5, 2.7]},
                    index = ['-20', '-15', '-10', '-5', '0', '5', '7'])
COP_6.index.name = 'T_aussenluft'

COP_8 = pd.DataFrame({'35':[2, 2.2, 2.5, 2.7, 3.4, 4, 4.6], 
                    '45':[1.5, 1.7, 2, 2.2, 2.8, 3.3, 3.8], 
                    '55':[1.7, 1.8, 2, 2, 2.1, 2.5, 3]}, 
                    index = ['-20', '-15', '-10', '-5', '0', '5', '9'])
COP_8.index.name = 'T_aussenluft'

COP_12 = pd.DataFrame({'35':[2, 2.2, 2.5, 2.9, 3.5, 4.1, 4.9], 
                    '45':[1.5, 1.8, 2, 2.3, 2.9, 3.4, 3.9], 
                    '55':[1.9, 2, 2, 2, 2.1, 2.5, 3.1]}, 
                    index = ['-20', '-15', '-10', '-5', '0', '5', '9'])
COP_12.index.name = 'T_aussenluft'


COP_16 = pd.DataFrame({'35':[2, 2.2, 2.5, 2.9, 3.5, 4.2, 4.9], 
                    '45':[1.6, 1.8, 2, 2.3, 2.9, 3.5, 3.9], 
                    '55':[1.8, 1.9, 2.1, 2, 2.2, 2.7, 3.1]}, 
                    index = ['-20', '-15', '-10', '-5', '0', '5', '9'])
COP_16.index.name = 'T_aussenluft'

COP = {
    'Nibe F2040-6': COP_6, # Heizleistung 35/55: 5/5
    'Nibe F2040-8': COP_8, # Heizleistung 35/55: 8/7
    'Nibe F2040-12': COP_12, # Heizleistung 35/55: 12/10
    'Nibe F2040-16': COP_16, # Heizleistung 35/55: 15/14
}

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

# Anwenden der Interpolation auf den COP- Dictionary
for key, df in COP.items():  # Iteriere über die Schlüssel und DataFrames im Dictionary
    interpolated_df = bilinear_interpolate(df)  # Interpolation für jedes DataFrame
    filename = f'COP_{key}.csv'  # Generiere den Dateinamen basierend auf dem Schlüssel
    interpolated_df.to_csv(filename, index=True)  # Speichern in einer CSV-Datei
