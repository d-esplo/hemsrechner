import pvlib
import pandas as pd # 'as pd' to change alias from pandas to pd
import matplotlib.pyplot as plt
import pgeocode

# Standort
plz = input("PLZ eingeben: ")
nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code(plz)
latitude = a['latitude']
longitude = a['longitude']

weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude, startyear = 2016, endyear = 2016)[0]
altitude = pvlib.location.lookup_altitude(latitude, longitude)
timezone = 'Etc/GMT-1'
location = latitude, longitude, altitude, timezone 
tmys = []
tmys.append(weather)

# Module & Wechselrichter
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
sapm_inverter = pvlib.pvsystem.retrieve_sam('cecinverter')
module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
inverter = sapm_inverter['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

# Eigene Module
# module = pvlib.ivtools.sdm.fit_desoto

system = {'module': module, 'inverter':inverter, 'surface_azimuth':180}
energies = {}
system['surface_tilt']=latitude
solpos=pvlib.solarposition.get_solarposition(
        time=weather.index,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        temperature=weather["temp_air"],
        pressure= pvlib.atmosphere.alt2pres(altitude),
)
dni_extra=pvlib.irradiance.get_extra_radiation(weather.index)
airmass=pvlib.atmosphere.get_relative_airmass(solpos['apparent_zenith'])
pressure=pvlib.atmosphere.alt2pres(altitude)
am_abs=pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
aoi=pvlib.irradiance.aoi(
        system['surface_tilt'],
        system['surface_azimuth'],
        solpos["apparent_zenith"],
        solpos["azimuth"],
)

total_irradiance=pvlib.irradiance.get_total_irradiance(
        system['surface_tilt'],
        system['surface_azimuth'],
        solpos['apparent_zenith'],
        solpos['azimuth'],
        weather['dni'],
        weather['ghi'],
        weather['dhi'],
        dni_extra=dni_extra,
        model='haydavies',

)
cell_temperature = pvlib.temperature.sapm_cell(
        total_irradiance['poa_global'],
        weather["temp_air"],
        weather["wind_speed"],
        **temperature_model_parameters,
    )

effective_irradiance=pvlib.pvsystem.sapm_effective_irradiance(
        total_irradiance['poa_direct'],
        total_irradiance['poa_diffuse'],
        am_abs,
        aoi,
        module,
    )

dc=pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
ac=pvlib.inverter.sandia(dc['v_mp'], dc['p_mp'], inverter)
annual_energy = ac.sum()
energies=annual_energy

# ac_monthly = ac.resample('m').sum()
# # df_monthly = 100 * (df_monthly.divide(ghi_monthly, axis=0) - 1)
# ac_monthly.plot()
# plt.show()

energies=pd.Series(energies)
print(energies)

energies.plot(kind='bar', rot=0)
plt.ylabel('Yearly energy yield (W hrs)')
plt.xlabel(plz)




