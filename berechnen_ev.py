import pandas as pd

ev_effizienz = 191 / 1000  # kWh per km
batteriekapazitaet = 72  # kWh
batterie_min = 10  # %
batterie_max = 80  # %
min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
max_ladeleistung = 11  # kW

def mit_pv(df, pv, homeoffice):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV_at_home']
    df['ev distanz'] = ev_aligned['distance_travelled']
    ev_soc = max_batterie_niveau

    df['überschuss'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        ladeleistung = 0
        pv_to_ev = 0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch = 0

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
            if ueberschuss >= ladeleistung:
                # Überschuss reicht aus, um die gewünschte Ladeleistung abzudecken
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
                eigenverbrauch += pv_to_ev
                ueberschuss -= ladeleistung
            elif ueberschuss > 0:
                # Teilweise Laden mit Überschuss, Rest aus dem Netz
                pv_to_ev = ueberschuss
                netzbezug += ladeleistung - ueberschuss
                ev_soc += ladeleistung
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
            else:
                # Kein Überschuss, Laden komplett aus dem Netz
                netzbezug += ladeleistung
                ev_soc += ladeleistung
        
        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'überschuss'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'ev distanz'] = ev_distanz

    return df

def mit_pvbs(df, pv, anlage_groesse, batteriekapazitaet, homeoffice):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/car_availability_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV_at_home']
    df['ev distanz'] = ev_aligned['distance_travelled']
    ev_soc = max_batterie_niveau
    
    # Batteriespeicher (BS)
    c_rate = 1
    bs_effizienz = 0.96  # BYD HVS & HVM
    min_soc = 1
    max_soc = batteriekapazitaet
    bs_soc = 5 

    if anlage_groesse<batteriekapazitaet:
        batteriekapazitaet = anlage_groesse
    
    bs_ladeleistung = c_rate * batteriekapazitaet * bs_effizienz  # kW


    ev_soc = max_batterie_niveau

    df['überschuss'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['BS to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0 

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        ladeleistung = 0
        pv_to_ev = 0
        bs_to_ev = 0
        bs_ladung = 0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch = 0
        entladung = 0
        netz_to_ev = 0

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

        bs_ladeleistung = c_rate * bs_soc * bs_effizienz  # kW

        # Step 4: Lade EV wenn Zuhause
        if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
            ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
            if ueberschuss >= ladeleistung:
                # Überschuss reicht aus, um die gewünschte Ladeleistung abzudecken
                ev_soc += ladeleistung
                pv_to_ev = ladeleistung
                eigenverbrauch += pv_to_ev
                ueberschuss -= ladeleistung
            elif ueberschuss > 0:
                # Teilweise Laden mit Überschuss, Rest aus dem Netz
                pv_to_ev = ueberschuss
                ev_soc += ladeleistung
                eigenverbrauch += pv_to_ev
                netzbezug += ladeleistung - pv_to_ev
                ueberschuss = 0
            else:
            # Kein Überschuss, Laden komplett aus dem Netz
                ev_soc += ladeleistung
                netzbezug += ladeleistung
                
        
        # Step 5: Strom von Netz?
        energiemangel = strombedarf + ladeleistung - pv_ertrag
        if energiemangel > 0:
            # Entlade Batterie, um Energiemangel zu decken
            potential_entladung = min(energiemangel/bs_effizienz, bs_ladeleistung)
            entladung = min(potential_entladung, bs_soc - min_soc)
            energie_aus_bs = entladung * bs_effizienz
            bs_soc -= entladung
            bs_to_ev = ladeleistung - pv_to_ev
            if energie_aus_bs >= bs_to_ev:
                bs_to_ev = ladeleistung - pv_to_ev 
            else:
                bs_to_ev = 0
            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            energiemangel_noch = energiemangel - energie_aus_bs
            netz_to_ev = ladeleistung - pv_to_ev - bs_to_ev
            netzbezug = max(energiemangel_noch, 0)
        else:
            entladung = 0

        if ueberschuss > 0 and netzbezug > 0:
            if netzbezug >= ueberschuss:
                netzbezug -= ueberschuss
                eigenverbrauch += ueberschuss
                ueberschuss = 0
            else:
                ueberschuss -= netzbezug
                eigenverbrauch += netzbezug
                netzbezug = 0

        df.loc[i, 'eigenverbrauch'] = eigenverbrauch
        df.loc[i, 'PV to EV'] = pv_to_ev
        df.loc[i, 'bs ladung'] = bs_ladung
        df.loc[i, 'BS to EV'] = bs_to_ev
        df.loc[i, 'überschuss'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'BS SOC'] = bs_soc
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'bs entladung'] = entladung
        df.loc[i, 'Netz to EV'] = netz_to_ev

    return df

def ersparnis_pv(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    pv_to_ev = round(sum(df['PV to EV']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    ev = round(sum(df['EV Ladung']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['EV Ladung']), 2)
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
        'strombedarf': strombedarf,
        'ev': ev,
        'pv': pv,
        'PV to EV': pv_to_ev,
        'eigenverbrauch': eigenverbrauch,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def ersparnis_pvbs(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['überschuss']))
    strombedarf = round(sum(df['Strombedarf']))
    pv_to_ev = round(sum(df['PV to EV']))
    pv_to_bs = round(sum(df['bs ladung']))
    bs_to_ev = round(sum(df['BS to EV']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    ev = round(sum(df['EV Ladung']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten_bs = round(netzbezug * strompreis, 2)

    # Stromkosten ohne PV
    verbrauch = round(sum(df['Strombedarf']+df['EV Ladung']), 2)
    stromkosten_ohne_pv = round(verbrauch * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round(stromkosten_ohne_pv - (stromkosten_bs - verguetung), 2)
    
    ergebnisse = {
        'strombedarf': strombedarf,
        'ev': ev,
        'pv': pv,
        'bs': pv_to_bs,
        'PV to EV': pv_to_ev,
        'BS to EV': bs_to_ev,
        'eigenverbrauch': eigenverbrauch,
        'netzbezug': netzbezug,
        'einspeisung': einspeisung,
        'stromkosten_ohne_pv': stromkosten_ohne_pv,
        'stromkosten_bs': stromkosten_bs,
        'verguetung': verguetung,
        'einsparung': einsparung
    }
    return ergebnisse

def print_ersparnis(ergebnisse):
    # Helper-Funktion: nur vorhandene Schlüssel anzeigen
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            print(f"{label}: {ergebnisse[key]}")

    # Print
    print_if_available('Haushaltsstrombedarf in kWh', 'strombedarf')
    print_if_available('EV Strombedarf in kWh', 'ev')
    print_if_available('Jahresertrag in kWh', 'pv')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'bs')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV')
    print('')  # Leere Zeile zur Trennung
    print_if_available('Netzbezug in kWh', 'netzbezug')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung')
    print('')  # Leere Zeile zur Trennung
    print_if_available('Stromkosten ohne PV in €/a', 'stromkosten_ohne_pv')
    print_if_available('Stromkosten mit PV in €/a', 'stromkosten')
    print_if_available('Stromkosten mit PV & BS in €/a', 'stromkosten_bs')
    print_if_available('Einspeisevergütung in €/a', 'verguetung')
    print_if_available('Stromkosten Einsparung in €/a', 'einsparung')


# def mit_hems(df):
#      # Step 3: Lade EV wenn Zuhause
#         if ev_zuhause == 1 and ev_soc < max_batterie_niveau:
#             ladeleistung = min(max_ladeleistung, max_batterie_niveau - ev_soc)
#             if ueberschuss >= 1.4:
#                 ladeleistung = min(ueberschuss, ladeleistung)
#                 ev_soc += ladeleistung
#                 pv_to_ev = ladeleistung
#                 eigenverbrauch += pv_to_ev
#             elif 0.9 < ueberschuss < 1.4:
#                 netzbezug += 1.4 - ueberschuss
#                 ladeleistung = min(1.4, ladeleistung)
#                 ev_soc += ladeleistung
#                 pv_to_ev = ueberschuss
#                 eigenverbrauch += pv_to_ev
#             else:
#                 netzbezug += ladeleistung
#                 ev_soc += ladeleistung
#     return