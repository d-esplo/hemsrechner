import pandas as pd
import streamlit as st

ev_effizienz = 191 / 1000  # kWh per km
batteriekapazitaet = 72  # kWh
batterie_min = 12  # % Deckt fahrt zur Arbeit
batterie_max = 80  # %
min_batterie_niveau = batterie_min / 100 * batteriekapazitaet  # kWh
max_batterie_niveau = batterie_max / 100 * batteriekapazitaet # kWh
max_ladeleistung = 11  # kW

# OHNE HEMS
# Berechnen 
def mit_pv(df, pv, homeoffice):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    ev_soc = max_batterie_niveau

    df['einspeisung'] = 0.0 
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
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz

    return df

def mit_pvbs(df, pv, bs_kapazitaet, homeoffice):
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    ev_soc = max_batterie_niveau

    # Batteriespeicher (BS)
    c_rate = 1
    bs_effizienz = 0.96  # BYD HVS & HVM
    min_soc = 1
    max_soc = bs_kapazitaet
    bs_soc = 0.5*bs_kapazitaet

    ev_soc = max_batterie_niveau

    df['einspeisung'] = 0.0 
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
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'BS SOC'] = bs_soc
        df.loc[i, 'BS %'] = bs_soc/bs_kapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'bs entladung'] = entladung
        df.loc[i, 'Netz to EV'] = netz_to_ev

    return df

# Ersparnis
def ersparnis_pv(df, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
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
    einspeisung = round(sum(df['einspeisung']))
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

# Print
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

def print_ersparnis_st(ergebnisse):
    # Helper-Funktion: nur vorhandene Schlüssel anzeigen
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            st.write(f"{label}: {ergebnisse[key]}")

    # Print
    print_if_available('Haushaltsstrombedarf in kWh', 'strombedarf')
    print_if_available('EV Strombedarf in kWh', 'ev')
    print_if_available('Jahresertrag in kWh', 'pv')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'bs')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV')
    ''  
    '' # Leere Zeile zur Trennung
    print_if_available('Netzbezug in kWh', 'netzbezug')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung')
    ''
    '' # Leere Zeile zur Trennung
    print_if_available('Stromkosten ohne PV in €/a', 'stromkosten_ohne_pv')
    print_if_available('Stromkosten mit PV in €/a', 'stromkosten')
    print_if_available('Stromkosten mit PV & BS in €/a', 'stromkosten_bs')
    print_if_available('Einspeisevergütung in €/a', 'verguetung')
    print_if_available('Stromkosten Einsparung in €/a', 'einsparung')

# MIT HEMS
# Berechnen mit HEMS
def mit_hems(df, pv, homeoffice):
    # Vergleich ohne HEMS
    df_ohne = mit_pv(df.copy(), pv, homeoffice)
    
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    df['next_day_ev_distanz'] = df.groupby(df.index.date)['ev distanz'].transform('sum').shift(-24)
    ev_soc = max_batterie_niveau
    ev_verbrauch_arbeit = 22*2*ev_effizienz

    df['einspeisung'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0
    df['ev_state'] = 0.0

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        next_ev_distanz = row['next_day_ev_distanz']
        # uhrzeit = row.name.hour 
        tag = row.name.dayofweek
        ladeleistung = 0.0
        pv_to_ev = 0.0
        netzbezug = 0.0
        ueberschuss = 0.0
        eigenverbrauch = 0.0
        lade = 0.0
        max_ev_laden = 0.0
        state = 0.0
        next_ev_verbrauch = 0.0
        next_ev_soc = 0.0

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch
        
        # Step 2: EV
        # 2.1: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz * ev_effizienz
            ev_soc = ev_soc - ev_verbrauch

        # 2.2: EV mit PV Laden, wenn zuhause
        if ev_zuhause == 1 and ev_soc < batteriekapazitaet and ueberschuss >= 0.9:
            lade = min(ueberschuss, 11)
            max_ev_laden = batteriekapazitaet - ev_soc
            # Stelle sicher, dass mindestens 1.4 kWh geladen werden
            if lade >= 1.4 and max_ev_laden >= 1.4:
                lade = min(lade, max_ev_laden)
                ev_soc += lade
                ueberschuss -= lade
                pv_to_ev += lade
                state += 1
            elif 0.9 < ueberschuss < 1.4:
                # Netz unterstutzt mit max. 500 W den Überschussladen
                netzbezug += 1.4 - ueberschuss
                ladeleistung = 1.4
                lade = 0
                ev_soc = min(ev_soc + ladeleistung, batteriekapazitaet)  # Begrenzung
                pv_to_ev += ueberschuss
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
                state += 2
            else:
                lade = 0
        else:
            lade = 0

        # 2.3: Berechne benötigte EV SOC für den nächsten Tag unter der Woche
        if homeoffice:
            if tag in [0, 2] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.1
            else:
                next_ev_soc = 0
        else:
            if tag in [0, 1, 2, 3, 6] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.2
            else:
                next_ev_soc = 0
            
        # 2.4 Berechne benötigte EV SOC für das Wochenende
        next_ev_verbrauch = next_ev_distanz * ev_effizienz
        if tag in [4, 5] and next_ev_verbrauch > ev_soc:
            next_ev_soc = next_ev_verbrauch + min_batterie_niveau
            state += 0.3
        else:
            next_ev_soc = 0

        # 2.5: EV Laden wenn notwendig für den nächsten Tag
        if ev_zuhause == 1 and ev_soc < next_ev_soc:
            ladeleistung = min(11, next_ev_soc - ev_soc)
            state = 0.4
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # 2.6: EV Laden wenn ev_soc < 10%
        if ev_zuhause == 1 and ev_soc < min_batterie_niveau:
            ladeleistung = min(11, min_batterie_niveau - ev_soc)
            state = 0.5
            if 0 < ladeleistung < 1.4:
                ladeleistung = 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # Überschuss und Netzbezug noch Mal prüfen
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
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung + lade
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'ev_state'] = state
    
    return df, df_ohne

def mit_hems_bs(df, pv, bs_kapazitaet, homeoffice):
    # Vergleich ohne HEMS
    df_ohne = mit_pvbs(df.copy(), pv, bs_kapazitaet, homeoffice)
    
    pv.index = pv.index.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    pv_aligned = pv.reindex(df.index).fillna(0)
    df['PV Ertrag'] = pv_aligned.values.astype(float)

    ev_profil = pd.read_csv(f'./Inputs/ev_homeoffice_{homeoffice}_2014.csv', index_col=0)
    ev_profil.index = pv.index.tz_localize(None)
    ev_profil.index = pd.to_datetime(df.index)
    ev_aligned = ev_profil.reindex(df.index).fillna(0)
    df['ev zuhause'] = ev_aligned['EV zuhause']
    df['ev distanz'] = ev_aligned['Distanz']
    df['next_day_ev_distanz'] = df.groupby(df.index.date)['ev distanz'].transform('sum').shift(-24)
    ev_soc = max_batterie_niveau
    ev_verbrauch_arbeit = 22*2*ev_effizienz
    
    # Batteriespeicher (BS)
    c_rate = 1
    bs_effizienz = 0.96  # BYD HVS & HVM
    min_soc = 1
    max_soc = bs_kapazitaet
    bs_soc = 0.5*bs_kapazitaet

    df['einspeisung'] = 0.0 
    df['eigenverbrauch'] = 0.0
    df['netzbezug'] = 0.0
    df['PV to EV'] = 0.0
    df['BS to EV'] = 0.0
    df['EV Ladung'] = 0.0
    df['EV SOC'] = 0.0
    df['ev_state'] = 0.0

    for i, row in df.iterrows():
        pv_ertrag = row['PV Ertrag']
        strombedarf = row['Strombedarf']
        ev_zuhause = row['ev zuhause']
        ev_distanz = row['ev distanz']
        next_ev_distanz = row['next_day_ev_distanz']
        uhrzeit = row.name.hour 
        tag = row.name.dayofweek
        ladeleistung = 0
        pv_to_ev = 0
        bs_to_ev = 0
        bs_ladung = 0
        netzbezug = 0
        ueberschuss = 0
        eigenverbrauch = 0
        entladung = 0
        netz_to_ev = 0
        lade = 0
        max_ev_laden = 0
        state = 0

        # Step 1: Überschuss nach Strombedarf
        if pv_ertrag >= strombedarf:
            ueberschuss = pv_ertrag - strombedarf
            eigenverbrauch = strombedarf
        else:
            ueberschuss = 0
            eigenverbrauch = pv_ertrag
            netzbezug = strombedarf - eigenverbrauch

        # Step 2: Lade BS mit Überschuss
        if ueberschuss > 0:
            ladepotenzial = ueberschuss * bs_effizienz
            bs_ladung = min(ladepotenzial, max_soc - bs_soc)
            bs_soc += bs_ladung
            ueberschuss -= (bs_ladung/bs_effizienz)
            eigenverbrauch += bs_ladung

        ueberschuss = max(0, ueberschuss)
        bs_ladeleistung = c_rate * bs_soc * bs_effizienz 
        
        # Step 3: EV
        # 3.1: Berechne EV Ladezustand
        if ev_zuhause == 0 and ev_distanz > 0:
            ev_verbrauch = ev_distanz * ev_effizienz
            ev_soc = ev_soc - ev_verbrauch

        # 3.2: EV mit PV Laden, wenn zuhause
        if ev_zuhause == 1 and ev_soc < batteriekapazitaet and ueberschuss >= 0.9:
            lade = min(ueberschuss, 11)
            max_ev_laden = batteriekapazitaet - ev_soc
            # Stelle sicher, dass mindestens 1.4 kWh geladen werden
            if lade >= 1.4 and max_ev_laden >= 1.4:
                lade = min(lade, max_ev_laden)
                ev_soc += lade
                ueberschuss -= lade
                pv_to_ev += lade
                state += 1
            elif 0.9 < ueberschuss < 1.4:
                # Netz unterstutzt mit max. 500 W den Überschussladen
                netzbezug += 1.4 - ueberschuss
                ladeleistung = 1.4
                lade = 0
                ev_soc = min(ev_soc + ladeleistung, batteriekapazitaet)  # Begrenzung
                pv_to_ev += ueberschuss
                eigenverbrauch += pv_to_ev
                ueberschuss = 0
                state += 2
            else:
                lade = 0

        # 3.3: Berechne benötigte EV SOC für den nächsten Tag unter der Woche
        if homeoffice:
            if tag in [0, 2] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.1
            else:
                next_ev_soc = 0
        else:
            if tag in [0, 1, 2, 3, 6] and ev_soc <= ev_verbrauch_arbeit:
                next_ev_soc = ev_verbrauch_arbeit + min_batterie_niveau
                state += 0.2
            else:
                next_ev_soc = 0
            
        # 3.4 Berechne benötigte EV SOC für das Wochenende
        next_ev_verbrauch = next_ev_distanz * ev_effizienz
        if tag in [4, 5] and next_ev_verbrauch > ev_soc:
            next_ev_soc = next_ev_verbrauch + min_batterie_niveau
            state += 0.3
        else:
            next_ev_soc = 0

        # 3.5: EV Laden wenn notwendig für den nächsten Tag
        notwendig = next_ev_soc + min_batterie_niveau
        if ev_zuhause == 1 and ev_soc < notwendig:
            ladeleistung += min(11, next_ev_soc)
            state = 0.4
            if 0 < ladeleistung < 1.4:
                ladeleistung += 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung

        # 3.6: EV Laden wenn ev_soc < 10%
        if ev_zuhause == 1 and ev_soc < min_batterie_niveau:
            ladeleistung += min(11, min_batterie_niveau-ev_soc)
            state = 0.5
            if 0 < ladeleistung < 1.4:
                ladeleistung += 1.4
                netzbezug += ladeleistung
                ev_soc += ladeleistung
            else:
                netzbezug += ladeleistung
                ev_soc += ladeleistung
        
        ladeleistung = ladeleistung + lade
        
        # Step 4: BS Entladen?
        if netzbezug > 0:
            # Entlade Batterie, um Energiemangel zu decken
            potential_entladung = min(netzbezug/bs_effizienz, bs_ladeleistung)
            entladung = min(potential_entladung, bs_soc - min_soc)
            energie_aus_bs = entladung * bs_effizienz
            bs_soc -= entladung
            bs_to_ev = ladeleistung - pv_to_ev
            if energie_aus_bs >= bs_to_ev:
                bs_to_ev = ladeleistung - pv_to_ev 
            else:
                bs_to_ev = 0
            # Übrige Energiemangel nach Batterienetladung = Netzbezug
            netzbezug_noch = netzbezug - energie_aus_bs
            netz_to_ev = ladeleistung - pv_to_ev - bs_to_ev
            netzbezug = max(netzbezug_noch, 0)
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
        df.loc[i, 'einspeisung'] = ueberschuss
        df.loc[i, 'EV Ladung'] = ladeleistung
        df.loc[i, 'netzbezug'] = netzbezug
        df.loc[i, 'EV SOC'] = ev_soc
        df.loc[i, 'EV %'] = ev_soc/batteriekapazitaet
        df.loc[i, 'BS SOC'] = bs_soc
        df.loc[i, 'BS %'] = bs_soc/bs_kapazitaet
        df.loc[i, 'ev distanz'] = ev_distanz
        df.loc[i, 'bs entladung'] = entladung
        df.loc[i, 'Netz to EV'] = netz_to_ev
        df.loc[i, 'ev_state'] = state

    return df, df_ohne

# Ersparnis mit HEMS
def ersparnis_hems(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    pv_to_ev = round(sum(df['PV to EV']))
    km = round(sum(df['ev distanz']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    ev = round(sum(df['EV Ladung']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten = round(netzbezug * strompreis, 2)
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten - verguetung), 2)
    co2 = round(((netzbezug_ohne-netzbezug)*0.380), 2) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    ergebnisse = {
        'strombedarf': strombedarf,
        'ev': ev,
        'km': km,
        'pv': pv,
        'PV to EV': pv_to_ev,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbaruch ohne': eigenverbrauch_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten': stromkosten,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2 
    }
    return ergebnisse

def ersparnis_hems_bs(df, df_ohne, anlage_groesse, strompreis):
    # Jahresertrag
    pv = round(sum(df['PV Ertrag']))
    netzbezug = round(sum(df['netzbezug']))
    netzbezug_ohne = round(sum(df_ohne['netzbezug']))
    einspeisung = round(sum(df['einspeisung']))
    einspeisung_ohne = round(sum(df_ohne['einspeisung']))
    strombedarf = round(sum(df['Strombedarf']))
    pv_to_ev = round(sum(df['PV to EV']))
    pv_to_bs = round(sum(df['bs ladung']))
    bs_to_ev = round(sum(df['BS to EV']))
    km = round(sum(df['ev distanz']))

    # Eingenverbrauch der PV-Produktion
    eigenverbrauch = round(sum(df['eigenverbrauch']))
    eigenverbrauch_ohne = round(sum(df_ohne['eigenverbrauch']))

    # Summe der aufgeladener Energie im Batteriespeicher & WP
    ev = round(sum(df['EV Ladung']))

    # Stromkosten mit PV
    # Strompreis 2024: 41,35 Cent/kWh (https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
    # strompreis = 0.4135
    stromkosten_bs = round(netzbezug * strompreis, 2)
    stromkosten_ohne = round(netzbezug_ohne * strompreis, 2)

    # Einspeisevergütung - Gewinn
    # Einspeisevergütung ab Feb 2025: bis 10 kWp: 7,96 ct, 10-40 kWp: 6,89 ct  (https://photovoltaik.org/kosten/einspeiseverguetung)
    if anlage_groesse <= 10:
        einspeiseverguetung = 0.0796
    else:
        einspeiseverguetung = 0.0689    
    verguetung = round(einspeisung * einspeiseverguetung, 2)
    verguetung_ohne = round(einspeisung_ohne * einspeiseverguetung, 2)

    # Ersparnis
    einsparung = round((stromkosten_ohne-verguetung_ohne) - (stromkosten_bs - verguetung), 2)
    co2 = (netzbezug_ohne-netzbezug*0.380) # CO₂-Emissionsfaktor Strommix 2023: 380 g/kWh
    ergebnisse = {
        'strombedarf': strombedarf,
        'ev': ev,
        'km': km,
        'pv': pv,
        'bs': pv_to_bs,
        'PV to EV': pv_to_ev,
        'BS to EV': bs_to_ev,
        'eigenverbrauch': eigenverbrauch,
        'eigenverbaruch ohne': eigenverbrauch_ohne,
        'netzbezug': netzbezug,
        'netzbezug ohne': netzbezug_ohne,
        'einspeisung': einspeisung,
        'einspeisung ohne': einspeisung_ohne,
        'stromkosten ohne': stromkosten_ohne,
        'stromkosten_bs': stromkosten_bs,
        'verguetung': verguetung,
        'verguetung ohne': verguetung_ohne,
        'einsparung': einsparung,
        'co2': co2
    }
    return ergebnisse

# Print mit HEMS auch Streamlit
def print_ersparnis_hems(ergebnisse):
    # Helper-Funktion: nur vorhandene Schlüssel anzeigen
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            print(f"{label}: {ergebnisse[key]}")

    # Print
    print_if_available('Haushaltsstrombedarf in kWh', 'strombedarf')
    print_if_available('EV Strombedarf in kWh', 'ev')
    print_if_available('Gefahrene km', 'km')
    print_if_available('Jahresertrag in kWh', 'pv')
    print_if_available('Eigenverbrauch in kWh', 'eigenverbrauch')
    print_if_available('Geladene PV-Strom in Batteriespeicher in kWh', 'bs')
    print_if_available('Geladene PV-Strom in Elektroauto in kWh', 'PV to EV')
    print_if_available('Geladene BS-Strom in Elektroauto in kWh', 'BS to EV')
    print('')
    print('Mit HEMS')  
    print_if_available('Netzbezug in kWh', 'netzbezug')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung')
    print_if_available('Einspeisevergütung in €/a', 'verguetung')
    print_if_available('Stromkosten mit PV & EV in €/a', 'stromkosten')
    print_if_available('Stromkosten mit PV, EV & BS in €/a', 'stromkosten_bs')
    print('')
    print('Ohne HEMS') 
    print_if_available('Netzbezug in kWh', 'netzbezug ohne')
    print_if_available('Einspeisung ins Netz in kWh', 'einspeisung ohne')
    print_if_available('Einspeisevergütung in €/a', 'verguetung ohne')
    print_if_available('Stromkosten in €/a', 'stromkosten ohne')
    print('')
    print('Einsparung mit HEMS')
    print_if_available('Stromkosten Einsparung in €/a', 'einsparung')

def print_ersparnis_hems_st(ergebnisse):
    # Helper-Funktion: nur vorhandene Schlüssel anzeigen
    def print_if_available(label, key):
        if key in ergebnisse and ergebnisse[key] is not None:
            st.write(f"- {label}: {ergebnisse[key]}")
    
    st.subheader("Ergebnisse", divider=True)
    row1 = st.columns(3)  # Erste Zeile: 3 Spalten
    row2 = st.columns(3)  # Zweite Zeile: 3 Spalten

    with row1[0]:
        with st.container(border=True):
            st.write('##### Strombedarf [kWh]')
            print_if_available('Haushalt', 'strombedarf')
            print_if_available('EV', 'ev')
    
    with row1[1]:
        with st.container(border=True):
            st.write("##### PV [kWh]")
            print_if_available('Jahresertrag', 'pv')
            print_if_available('Eigenverbrauch', 'eigenverbrauch')
            print_if_available('PV to EV', 'PV to EV')

    with row1[2]:
        with st.container(border=True):
            st.write("##### BS [kWh]")
            print_if_available('PV to BS', 'bs')
            print_if_available('BS to EV', 'BS to EV')

    with row2[0]:
        with st.container(border=True):
            st.write("##### Ohne HEMS")
            print_if_available('Netzbezug [kWh]', 'netzbezug ohne')
            print_if_available('Einspeisung [kWh]', 'einspeisung ohne')
            print_if_available('Einspeisevergütung [€/a]', 'verguetung ohne')
            print_if_available('Stromkosten [€/a]', 'stromkosten ohne')

    with row2[1]:
        with st.container(border=True):
            st.write("##### Mit HEMS")
            print_if_available('Netzbezug [kWh]', 'netzbezug')
            print_if_available('Einspeisung [kWh]', 'einspeisung')
            print_if_available('Einspeisevergütung [€/a]', 'verguetung')
            print_if_available('Stromkosten [€/a]', 'stromkosten')
            print_if_available('Stromkosten [€/a]', 'stromkosten_bs')

    with row2[2]:
            with st.container(border=True):
                st.write("##### Einsparung [€/a]")
                print_if_available('mit HEMS [€/a]', 'einsparung')
                print_if_available('mit HEMS [kg CO₂/a]', 'co2')



    