import pandas as pd 
import matplotlib.pyplot as plt
from datetime import time as settime
from demandlib import bdew
import demandlib.bdew as bdew
from workalendar.europe import Germany

def get_demandlib_profil(jahr, strombedarf):
    cal = Germany()
    holidays = dict(cal.holidays(jahr))

    ann_el_demand_per_sector = {
        "h0": strombedarf,
        "h0_dyn": strombedarf,
    }

    # read standard load profiles
    e_slp = bdew.ElecSlp(jahr, holidays=holidays)

    # multiply given annual demand with timeseries
    elec_demand = e_slp.get_profile(ann_el_demand_per_sector)

    # Plot demand normal & dynamisch
    elec_demand_resampled = elec_demand.resample("h").mean() 
    ax = elec_demand_resampled.plot()
    ax.set_xlabel("Date")
    ax.set_ylabel("Power demand")
    plt.show()
    return elec_demand_resampled, plt
