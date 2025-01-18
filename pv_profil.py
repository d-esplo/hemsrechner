import pvlib
import pandas as pd 
import pgeocode

def get_pv_profil(plz, jahr, anlage_groesse):
    ## Standort 
    nomi = pgeocode.Nominatim('de') 
    a = nomi.query_postal_code(plz)
    latitude = a['latitude']
    longitude = a['longitude']

    ## PV Jahresprofil 
    # Get hourly solar irradiation and modeled PV power output from PVGIS
    data = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=jahr, end=jahr, surface_tilt=35,
                                                        pvcalculation=True, peakpower=anlage_groesse, mountingplace='building')  
    pv_ertrag = data['P']
    pv_ertrag =pv_ertrag.resample('h').sum()
    
    return pv_ertrag