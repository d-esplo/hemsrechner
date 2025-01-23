import pandas as pd

jahr = 2014
stunden_im_jahr = 8760
ev_effizienz = 191 / 1000  # kWh per km
batteriekapazitaet = 72  # kWh
batterie_min = 10  # %
batterie_max = 80  # %
min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
max_ladeleistung = 11  # kW

# Battery parameters
c_rate = 1
bs_effizienz = 0.96  # BYD HVS & HVM
min_soc = 1
max_soc = bs_kapazitaet
bs_soc = 5 


def mit_pv(df, pv, homeoffice):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    df['ev zuhause'] = ev_profil['EV_at_home']
    df['ev distanz'] = ev_profil['distance_travelled']
    ev_soc = max_batterie_niveau

    df['überschuss'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['EV Energiegesamt'] = 0.0
    df['EV SOC'] = 0.0

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch
        
        # Step 2: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz*ev_effizienz
            if ev_soc - ev_verbrauch >= min_batterie_niveau:
                ev_soc -= ev_verbrauch
            else:
                ev_distanz = (ev_soc - min_batterie_niveau)/ev_effizienz
                ev_soc = min_batterie_niveau

        # Step 3: Lade EV wenn Zuhause
        if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
            ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
            if ueberschuss >= 1.4:
                ladeleistung = min(ueberschuss, ladeleistung)
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
            elif 0.9 < ueberschuss < 1.4:
                netzbezug += 1.4 - ueberschuss
                ladeleistung = min(1.4, ladeleistung)
                ev_soc += ladeleistung
                pv_to_ev = ueberschuss
        
        ev_energie = pv_to_ev + netzbezug

        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'überschuss'] = ueberschuss
        df.loc[i, 'EV Energiegesamt'] = ev_energie
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc

    return df

def mit_pvbs(df, pv, anlage_groesse, bs_kapazitaet):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    df['ev zuhause'] = ev_profil['EV_at_home']
    df['ev distanz'] = ev_profil['distance_travelled']
    
    # Batteriespeicher (BS)
    c_rate = 1
    bs_effizienz = 0.96  # BYD HVS & HVM
    min_soc = 1
    max_soc = bs_kapazitaet
    bs_soc = 5 

    ev_soc = max_batterie_niveau

    df['überschuss'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['PV to BS'] = 0.0
    df['BS to EV'] = 0.0
    df['EV Energiegesamt'] = 0.0
    df['EV SOC'] = 0.0 

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch
        
        # Step 2: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz*ev_effizienz
            if ev_soc - ev_verbrauch >= min_batterie_niveau:
                ev_soc -= ev_verbrauch
            else:
                ev_distanz = (ev_soc - min_batterie_niveau)/ev_effizienz
                ev_soc = min_batterie_niveau
        
        # Step 3: Lade BS mit Überschuss
        if ueberschuss > 0:
            ladepotenzial = ueberschuss * bs_effizienz
            bs_ladung = min(ladepotenzial, max_soc - bs_soc)
            bs_soc += bs_ladung
            ueberschuss -= (bs_ladung/bs_effizienz)
            eigenverbrauch += bs_ladung

        # Step 4: Lade EV wenn Zuhause
        if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
            ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
            if ueberschuss >= 1.4:
                ladeleistung = min(ueberschuss, ladeleistung)
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
            elif 0.9 < ueberschuss < 1.4:
                netzbezug += 1.4 - ueberschuss
                ladeleistung = min(1.4, ladeleistung)
                ev_soc += ladeleistung
                pv_to_ev = ueberschuss
                eigenverbrauch += ueberschuss
            elif pv_ertrag < anlage_groesse and bs_soc > 1.4:
                bs_verfuegbar = max(0, anlage_groesse - pv_ertrag)
                ladeleistung = min(bs_verfuegbar, ladeleistung)
                ev_soc += ladeleistung
                bs_to_ev += ladeleistung
                bs_soc -= ladeleistung
            elif 20 >= ev_soc > min_batterie_niveau:
                ladeleistung = min(1.4, ladeleistung)
                ev_soc += ladeleistung
                netzbezug += ladeleistung

        ev_energie = pv_to_ev + netzbezug

        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'PV to BS'] = pv_to_bs
        df.loc[i, 'BS to EV'] = bs_to_ev
        df.loc[i, 'überschuss'] = ueberschuss
        df.loc[i, 'EV Energiegesamt'] = ev_energie
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'BS SOC'] = bs_soc

    return