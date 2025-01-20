import numpy as np
import pandas as pd

def wp_ohne_pv(lastprofil_h, Q_ps, PS_verlust):
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
        temp_mittel = df.loc[time, 'temp_mittel']
        heizwaermebedarf = df.loc[time, 'Heizwärmebedarf']
        heizleistung = df.loc[time, 'Heizleistung']
        heizleistung_neu = df.loc[time, 'Heizleistung neu']
        waerme_ps = df.loc[time, 'Wärmegehalt PS']
        waerme_ps_p = df.loc[previous_time, 'Wärmegehalt PS']
        ladezustand_ps = df.loc[time, 'Ladezustand PS']
       
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
    
    df.loc[df['Heizleistung neu'] == 0, 'COP'] = 0
    # Filtere die Werte, bei denen Heizleistung neu > 0
    cop_filtered = df[df['Heizleistung neu'] > 0]['COP']
    cop_mean = cop_filtered.mean()

    df['elekt. Leistungaufnahme'] = df['Heizleistung neu']/df['COP']
    df['therm. Entnahmelesitung'] = df['Heizleistung'] - df['elekt. Leistungaufnahme']

    print('P_el [kW/a]: ', round(df['elekt. Leistungaufnahme'].sum(), 2))
    print('Stromkosten WP [€/a]:', round(df['elekt. Leistungaufnahme'].sum()*0.358, 2)) # Strompreis Dezember 24 Bestandkunden €/kWh
    print('COP: ', round(cop_mean, 2))

    return df

def wp_mit_pv( ):
    
    return