## !! FUNKTIONIERT NICHT OHNE LPG PROGRAMM !!
# habe utlis.py kopiert und in Ordner gespeichert, ohne geht das auch nicht

from pylpg import lpg_execution, lpgdata
import utils

# Simulate the predefined household CHR01 (couple, both employed) for the year 2022
data = lpg_execution.execute_lpg_single_household(
    2022,
    lpgdata.Households.CHR01_Couple_both_at_Work,
    lpgdata.HouseTypes.HT20_Single_Family_House_no_heating_cooling,
)

# Extract the generated electricity load profile
electricity_profile = data["Electricity_HH1"]
print(electricity_profile)

# Resample to 15 minute resolution
profile = electricity_profile.resample("15min").sum()

# Show a carpet plot
utils.carpet_plot(profile)

