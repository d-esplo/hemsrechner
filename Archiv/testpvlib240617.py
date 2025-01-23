import pvlib
import pandas as pd # 'as pd' to change alias from pandas to pd
import matplotlib.pyplot as plt


# Das funktioniert nicht:

## SAM_URL = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv'
# modules = pvlib.pvsystem.retrieve_sam(path=SAM_URL)
# trina_module= modules['Trina Solar TSM-420DE15M(II)']
# print(trina_module)

# Das funktioniert auch nicht

# cec_modules = pvlib.pvsystem.retrieve_sam('cecmod')
# sapm_inverter = pvlib.pvsystem.retrieve_sam('cecinverter')

# ## Jinko Solar Co. Ltd JKM400M-72L-V in CEC modules
# module = cec_modules['Jinko_Solar_Co._Ltd_JKM400M_72L_V']
# inverter = sapm_inverter['ABB__MICRO_0_25_I_OUTD_US_208__208V_']


# system dictionary
system = {'module':module, 'inverter':inverter, 'surface_azimuth':180}

# Standort: Düsseldorf Benrath 51.158193, 6.863696
latitude = 6.863696
longitude = 51.158193
name = 'Duesseldorf-Benrath'
altitude = 38
timezone = 'Etc/GMT-2'

location = latitude, longitude, name, altitude, timezone

# Wetter tmy: Typical Metheorological Year between 2013-2023
weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude, startyear=2013, endyear=2023, map_variables=True)[0]
weather.index.name = "utc_time"

'Jinko_Solar_Co__Ltd_JKM400M_72L_V' in cec_modules
