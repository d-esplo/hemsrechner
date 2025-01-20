import pandas as pd
from datetime import timedelta

def get_jahresenergiebedap(baujahr, flaeche, anzahl_personen, strombedarf):
    ## Jahresenergiebedarf: 
    # Heizwärmebedarf & Heizlast
    waerme_tabelle = pd.read_excel('./Inputs/waermebedarf.xlsx')
    waerme_tabelle.set_index('Baujahr', inplace=True)
    heizlast = waerme_tabelle.loc[baujahr, 'Heizlast [W/m^2]']*flaeche/1000 # in kW
    waermebedarf = waerme_tabelle.loc[baujahr, 'Wärmebedarf [kWh/m^2]']*flaeche # in kWh

    # Warmwasserbedarf / Trinkwassererwärmung
    twebedarf = anzahl_personen*500 # Annahme VDI 4655: 500 kWh/Person im EFH

    # Strombedarf
    strombedarf_list = [
        [1, 2350],
        [2, 2020*2],
        [3, 1660*3], 
        [4, 1500*4],
        [5, 1400*5],
        [6, 1350*6]
    ] # [kWh]

    if strombedarf == 0:
        for anzahl in strombedarf_list:
            if anzahl[0] == anzahl_personen:
                strombedarf = anzahl[1]
    
    return heizlast, waermebedarf, twebedarf, strombedarf


def get_lastprofile(waermebedarf, strombedarf, twebedarf, flaeche, TRY_region, anzahl_personen):
    ## Energiefaktoren nach Typtage und TRY-Region
    # Bestand oder Niedrigenergiehaus (NEH) 
    # Energiefaktoren Tabellen einlesen
    if waermebedarf/flaeche < 40:
        # NEH
        bau = 'NEH'
        energiefaktoren_heiz = pd.read_excel('./Inputs/Heiz_Energiefaktoren_TRY2017_EFH_NEH.xlsx')
        energiefaktoren_heiz.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_heiz.index.name = 'TRY'
        energiefaktoren_strom = pd.read_excel('./Inputs/Strom_Energiefaktoren_TRY2017_EFH_NEH.xlsx')
        energiefaktoren_strom.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_strom.index.name = 'TRY'
        energiefaktoren_twe = pd.read_excel('./Inputs/TWE_Energiefaktoren_TRY2017_EFH_NEH.xlsx')
        energiefaktoren_twe.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_twe.index.name = 'TRY'
    else:
        # Bestand
        bau = 'Bestand'
        energiefaktoren_heiz = pd.read_excel('./Inputs/Heiz_Energiefaktoren_TRY2017_EFH_Bestand.xlsx')
        energiefaktoren_heiz.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_heiz.index.name = 'TRY'
        energiefaktoren_strom = pd.read_excel('./Inputs/Strom_Energiefaktoren_TRY2017_EFH_Bestand.xlsx')
        energiefaktoren_strom.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_strom.index.name = 'TRY'
        energiefaktoren_twe = pd.read_excel('./Inputs/TWE_Energiefaktoren_TRY2017_EFH_Bestand.xlsx')
        energiefaktoren_twe.set_index('Unnamed: 0', inplace=True)
        energiefaktoren_twe.index.name = 'TRY'

    ## Ermittlung von Tagesenergiebedarfen - Gleichungen 1 bis 3 (VDI 4655)
    tagesenergiebedarf = pd.DataFrame({'ÜWH':[None], 'ÜWB':[None], 'ÜSH':[None], 'ÜSB':[None], 
                        'SWX':[None], 'SSX':[None],
                        'WWH':[None], 'WWB':[None], 'WSH':[None], 'WSB':[None]}, index = ['heiz_tag', 'strom_tag', 'twe_tag'])
    tagesenergiebedarf.index.name = 'Tagesenergiebedarf [kWh]'

    for idx in tagesenergiebedarf.index:
        for spalte in tagesenergiebedarf.columns:
            if idx == 'heiz_tag':  # Heizenergiebedarf [kWh]
                tagesenergiebedarf.loc[idx, spalte] = round(energiefaktoren_heiz.loc[5, spalte] * waermebedarf, 2)
            elif idx == 'strom_tag':  # Strombedarf [kWh]
                tagesenergiebedarf.loc[idx, spalte] = round(strombedarf * (energiefaktoren_strom.loc[TRY_region, spalte] * anzahl_personen + 1 / 365), 2)
            elif idx == 'twe_tag':  # TWE Bedarf [kWh]
                tagesenergiebedarf.loc[idx, spalte] = round(twebedarf * (energiefaktoren_twe.loc[TRY_region, spalte] * anzahl_personen + 1 / 365), 2)

    # Spaltennamen im lastprofil-DataFrame ändern
    tagesenergiebedarf = tagesenergiebedarf.rename(
        columns={
            "ÜWH": "UWH",
            "ÜWB": "UWB",
            "ÜSH": "USH",
            "ÜSB": "USB"
        }
    )

    ## Referenzlastprofile Tabellen einlesen
    # Pfad zur Excel-Datei
    if bau == 'Bestand':
        excel_rlp = './Inputs/Referenzlastprofile_EFH_Bestand_15_Min.xlsx'
        excel_verteilung = './Inputs/Typtagverteilung_TRY_Bestand.xlsx'
    else:
        excel_rlp = './Inputs/Referenzlastprofile_EFH_NEH_15_Min.xlsx'
        excel_verteilung = './Inputs/Typtagverteilung_TRY_NEH.xlsx'
    
    # Alle Tabellen in einem Dictionary einlesen
    referenzlastprofile = pd.read_excel(excel_rlp, sheet_name=None)

    # Beispiel: Schlüssel von 'ÜSB' -> 'SB', 'ÜWB' -> 'WB', etc.
    referenzlastprofile_renamed = {
        key.replace('Ü', 'U'): value  # Ersetze 'Ü' durch U 
        for key, value in referenzlastprofile.items()
    }

    # Optional: Original-Dictionary überschreiben
    referenzlastprofile = referenzlastprofile_renamed

    ## 15 Min Lastprofile für jeden Tagestyp erstellen
    # Referenzlastprofile * Tagesenergiebedarf

    # Ergebnisse speichern - Dictionary
    ergebnisse = {}

    # Iteration über Tabellen in referenzlastprofile_bestand
    for tabellenname, df in referenzlastprofile.items():

        # Prüfen, ob der Tabellenname als Spalte in tagesenergiebedarf existiert
        if tabellenname not in tagesenergiebedarf.columns:
            print(f"Tabelle {tabellenname} hat keinen passenden Spaltennamen in Tagesenergiebedarf.")
            continue

        # Zuordnung der Zielspalten zu den entsprechenden Zeilen in tagesenergiebedarf
        zeilen_zuordnung = {
        'Heizwärme normiert ': 'heiz_tag',  # Heizwärme normiert wird mit heiz_tag verknüpft
        'Strombedarf normiert': 'strom_tag',  # Strombedarf normiert wird mit strom_tag verknüpft
        'Warmwasser normiert': 'twe_tag'  # Warmwasser normiert wird mit twe_tag verknüpft
        }

        # Schleife durch die Zielspalten und Skalierung anwenden
        for spalte in ['Heizwärme normiert ', 'Strombedarf normiert', 'Warmwasser normiert']:
            if spalte in df.columns:  # Überprüfen, ob die Spalte in der Tabelle existiert
                # Verwende die Zeilenbezeichnung aus der Zuordnung, um den richtigen Faktor zu erhalten
                zeilenbezeichnung = zeilen_zuordnung[spalte]
                faktor = tagesenergiebedarf.loc[zeilenbezeichnung, tabellenname]
                
                # Skalieren der Spalte
                df[spalte] = df[spalte] * faktor
            # else: # Debugging
            # print(f"Spalte {spalte} existiert nicht in Tabelle {tabellenname}.")

        # Bearbeitete Tabelle speichern
        ergebnisse[tabellenname] = df

    # Typtag Verteilung einlesen
    verteilung_bestand = pd.read_excel(excel_verteilung)
    verteilung_bestand.set_index('Unnamed: 0', inplace=True)
    verteilung_bestand.index.name = 'Datum'

    ## Lastprofile 
    # ***Offen***: Urlaub berücksichtigen (siehe Abschnitt 2 DIN 4655)

    # Neuer DataFrame für das kombinierte Lastprofil
    lastprofil = pd.DataFrame()

    # Schleife über die Zeilen von verteilung_bestand (für jeden Tag in 2014), überspringe die erste Zeile
    for index, row in verteilung_bestand.iloc[1:].iterrows():  # Start ab der zweiten Zeile
        # Suche die Spalte, die dem TRY_region entspricht
        passende_spalte = None
        for spalte in verteilung_bestand.columns:
            if spalte == TRY_region:  # Direktvergleich mit numerischem TRY_region-Wert
                passende_spalte = spalte
                break

        # Wenn keine passende Spalte gefunden wurde, Debug-Info ausgeben
        if passende_spalte is None:
            # print(f"Keine passende Spalte für TRY_region {TRY_region} gefunden.")
            continue

        # Hole den Typtag aus der passenden Spalte
        typtag = row[passende_spalte]

        # Überprüfen, ob Typtag tatsächlich gültig ist
        if not isinstance(typtag, str) or typtag.strip() == '':
            # print(f"Ungültiger Typtag in Zeile {index}: {typtag}")
            continue

        # Debug-Ausgabe für den gefundenen Typtag
        # print(f"Tag {index}, TRY_region '{TRY_region}', Typtag: {typtag}")

        # Überprüfen, ob Typtag im ergebnisse-Dictionary existiert
        if typtag in ergebnisse:
            # Hole die entsprechende Tabelle aus dem Dictionary
            # profil = ergebnisse[typtag]
            # Kopiere nur die gewünschten Spalten aus der Tabelle
            profil = ergebnisse[typtag][["Strombedarf normiert", "Warmwasser normiert", "Heizwärme normiert "]]


            # Debug-Ausgabe, wenn das Profil gefunden wird
            # print(f"Profil für Typtag '{typtag}' gefunden, füge hinzu.")

            # Erstelle eine neue Spalte mit dem vollständigen Datum für 15-Minuten-Taktung
            datum = pd.Timestamp(index)  # Annahme: Datum in gültigem Format
            zeitraum = [datum + timedelta(minutes=15 * i) for i in range(len(profil))]  # 15-Minuten-Zeitschritte
            profil = profil.copy()  # Vermeidet das Modifizieren des Originals
            profil['Zeit'] = zeitraum  # Füge die Zeitschritte hinzu

            # Füge das Profil in den neuen DataFrame ein
            lastprofil = pd.concat([lastprofil, profil])
        #else:
            # Debug-Ausgabe, wenn der Typtag nicht gefunden wird
            # print(f"Typtag '{typtag}' nicht in ergebnisse gefunden.")

    # Index des resultierenden DataFrames zurücksetzen
    lastprofil.reset_index(drop=True, inplace=True)
    lastprofil.set_index('Zeit', inplace=True)

    # Spaltennamen im lastprofil-DataFrame ändern
    lastprofil = lastprofil.rename(
        columns={
            "Strombedarf normiert": "Strombedarf",
            "Warmwasser normiert": "Warmwasserbedarf",
            "Heizwärme normiert ": "Heizwärmebedarf"
        }
    )

    lastprofil_h = lastprofil.resample('1h').sum()

    return lastprofil_h
