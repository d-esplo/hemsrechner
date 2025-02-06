import pandas as pd
import numpy as np

jahr = 2014
stunden = 8760
distanz_arbeit = 22  # km Einweg
max_fahrt_distanz = 100  # km Wochenendetrips

def ev_profil():
    for homeoffice in [True, False]:
        verfuegbar = np.ones(stunden) 
        distanz = np.zeros(stunden)  
        date_index = pd.date_range(start=f'{jahr}-01-01', periods=stunden, freq='h')
        
        for i in range(0, stunden, 24):  
            current_day = date_index[i].dayofweek  # 0=Montag, 6=Sonntag
            
            if homeoffice:
                # Pendeln nur Dienstags und Donnerstags
                if current_day in [1, 3]: 
                    # EV fährt um 7 Uhr los & kommt zuhause um 16 Uhr an
                    verfuegbar[i + 7:i + 16] = 0  # EV nicht zuhause
                    distanz[i + 7] = distanz_arbeit  # Fahrt zur Arbeit
                    distanz[i + 15] = distanz_arbeit # Fahrt nach Hause
                else:
                    # Mo, Mi, Fr ist das EV zuhause
                    verfuegbar[i:i + 24] = 1  
            else:
                # Kein Homeoffice: pendeln Mo-Fr
                if current_day in range(5):  
                    # EV fährt um 7 Uhr los & kommt zuhause um 16 Uhr an
                    verfuegbar[i + 7:i + 16] = 0  # EV nicht zuhause
                    distanz[i + 7] = distanz_arbeit  # Fahrt zur Arbeit
                    distanz[i + 15] = distanz_arbeit  # Fahrt nach Hause

            # Random Wochenende Trips
            if current_day in [5, 6]:  # Sa-So
                if np.random.rand() < 0.5:  # Random ob Wochenende Trip stattfindet oder nicht
                    fahrt_distanz = np.random.randint(10, max_fahrt_distanz + 1)  # Random distanz (10 bis 100 km)
                    
                    # Set Abfahrt
                    start_hour = np.random.randint(7, 14)  # Random Abfahrt Zeit
                    return_hour = start_hour + np.random.randint(2, 5)  # Nicht zuhause random 2 bis 4 Stunden
                    
                    # Rückfahrt am gleichen Tag
                    if return_hour < i + 24:
                        # Verfügbar = 0 wenn ev nicht zuhause, fahrt_distanz zuweisen
                        verfuegbar[i + start_hour: i + return_hour + 1] = 0
                        distanz[i + start_hour] = fahrt_distanz  
                        distanz[i + return_hour] = fahrt_distanz  

        # Ergebnisse in CSV-Datei speichern
        profil_name = f'ev_homeoffice_{homeoffice}_{jahr}.csv'
        pd.DataFrame({'EV zuhause': verfuegbar, 'Distanz': distanz}, index=date_index).to_csv(profil_name)

# Run this function to generate and save the profiles
if __name__ == "__main__":
    ev_profil()

