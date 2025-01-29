import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# COP Lineare Regression

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

def COP_regression(df):
    # Neue Werte für die Extrapolation mit einem Schritt von 0.5°C
    t_vor_new = np.arange(35, 60.5, 0.5)  # Vorlauftemperaturen bis 60°C
    t_aussen_new = np.arange(-20, 14.5, 0.5)  # Außentemperaturen bis 14°C

    # Vorbereitung der Daten für die Regression
    X_train = np.array([(x, y) for x in df.columns.astype(float) for y in df.index.astype(float)])
    y_train = df.values.flatten()

    # Lineares Regressionsmodell trainieren
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Vorhersage für neue Werte
    X_pred = np.array([(x, y) for x in t_vor_new for y in t_aussen_new])
    y_pred = model.predict(X_pred)

    # Umwandlung in DataFrame
    cop_regression = pd.DataFrame(y_pred.reshape(len(t_aussen_new), len(t_vor_new)), 
                                index=t_aussen_new, columns=t_vor_new)
    cop_regression.index.name = 'T_aussenluft'
    return cop_regression

# Anwenden der Regression auf den COP- Dictionary
for key, df in COP.items():  
    regression_df = COP_regression(df)  
    filename = f'COP_{key}_regression.csv'  
    regression_df.to_csv(filename, index=True)  