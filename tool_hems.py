# In Terminal eingeben:
# streamlit run tool_hems.py --server.port 5996

import streamlit as st
import pandas as pd
import temperatur_aussen, try_region, lastprofile_VDI4655, heizkurve, pv_profil, berechnen_bs, berechnen_ev, berechnen_wp

# Strompreis
strompreis = 0.358

# Titel
st.title('Berechnungstool HEMS')
st.header('Stromkosten einsparen mit PV, BS, EV, WP & HEMS')

# Variable Abfrage
col1, col2, col3 = st.columns(3)

with col1:
    ':blue[Haus Information:]'
    plz = st.text_input('Postleitzahl')
    flaeche = st.number_input(
    "Hausfläche", value=None, placeholder="in m²"
    )
    baujahr = st.selectbox(
    "Baujahr",
    ("Vor 1918", "1919 - 1948", "1949 - 1957", "1958 - 1968", "1969 - 1978", "1979 - 1983", "1984 - 1994", "1995 - 2001", "Nach 2002", "KfW 85", "KfW 70", "KfW 55", "KfW 40", "Passivhaus"))
    anzahl_personen = st.number_input("Hausbewohner", value=0, placeholder="Anzahl")

with col2:
   strombedarf = st.number_input("Strombedarf", value = None, placeholder ='in kWh')
   strompreis = st.number_input('Strompreis', value=None, placeholder = 'in Cent')
   ':blue[Komponenten Auswahl: ]'
   anlage_groesse = st.number_input("PV Anlage",  value = None, placeholder = 'Größe in kWp')
   komponenten = ["Batteriespeicher", "EV"]#, "Wärmepumpe"]
   selection = st.multiselect("Komponenten", komponenten)

with col3:
    if "Batteriespeicher" in selection:
        battery_capacity = st.number_input("Batteriespeicher", value = None, placeholder = 'Kapazität in kWh')
    
    if "EV" in selection:
        homeoffice = st.selectbox("Homeoffice", (True, False))

    # if "Wärmepumpe" in selection:
    #    heizung = st.selectbox("Heizung", ("Heizkörper", "Fußbodenheizung"))

# Lastprofile für Strom, Heizung, PV und T_ausssen generieren
h, w, twe, s = lastprofile_VDI4655.get_jahresenergiebedarf(baujahr, flaeche, anzahl_personen, strombedarf)
TRY_region, T_n_aussen = try_region.get_try_t_n_aussen(int(plz))
df = lastprofile_VDI4655.get_lastprofile(w, s, twe, flaeche, TRY_region, anzahl_personen)
df['T_aussen'] = temperatur_aussen.get_hourly_temperature(plz, 2014)
pv = pv_profil.get_pv_profil(plz, 2014, anlage_groesse)
strompreis = strompreis/100

# Für WP (+ PV, + BS, + LS)
# if "Wärmepumpe" in selection:

#     # WP, Heizleistung, Heizkurve
#     hz, T_soll, T_n_vor, T_n_rueck = heizkurve.get_heizkurve(heizung, df['T_aussen'], T_n_aussen)
#     df['T_vor'] = hz['T_vor']
#     df['T_rueck'] = hz['T_rueck']
#     wp_groesse = berechnen_wp.get_waermepumpe(h)
#     heizleistung_auslegung = heizkurve.get_heizleistung(T_n_aussen, h, T_soll)
#     df = heizkurve.get_heizleistung_profil(df, heizleistung_auslegung)
#     df = heizkurve.get_cop(wp_groesse, df)
#     V_ps, PS_verlust, Q_ps = berechnen_wp.get_pufferspeicher(h, T_n_vor, T_n_rueck)
    
#     # Basis Programm - ohne PV
#     df, P_el, COP = berechnen_wp.ohne_pv(df, Q_ps, PS_verlust)

#     if "Batteriespeicher" and "EV" in selection:
#         df_bsev = berechnen_wp.mit_pvbsev(df.copy(), pv, anlage_groesse, battery_capacity, homeoffice)
#         ergebnisse = berechnen_wp.ersparnis_evbs(df_bsev, anlage_groesse, strompreis)
#         plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'battery_soc', 'EV Ladung', 'elekt. Leistungaufnahme']
#         df_plt = df_bsev.copy()
#     elif "Batteriespeicher" in selection:
#         df_bs = berechnen_wp.mit_pvbs(df.copy(), pv, anlage_groesse, battery_capacity)
#         ergebnisse = berechnen_wp.ersparnis_bs(df_bs, anlage_groesse, strompreis)
#         plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'battery_soc', 'elekt. Leistungaufnahme']  
#         df_plt = df_bs.copy()
#     elif "EV" in selection:
#         df_ev = berechnen_wp.mit_pvev(df.copy(), pv, homeoffice)
#         ergebnisse = berechnen_wp.ersparnis_ev(df_ev, anlage_groesse, strompreis)
#         plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'EV Ladung', 'elekt. Leistungaufnahme']
#         df_plt = df_ev.copy()
#     else: 
#         # nur WP & PV 
#         df_wp = berechnen_wp.mit_pv(df.copy(), pv)
#         ergebnisse = berechnen_wp.ersparnis_pv(df_wp, anlage_groesse, strompreis)
#         plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'elekt. Leistungaufnahme']
#         df_plt = df_wp.copy()
    
#     berechnen_wp.print_ersparnis_st(ergebnisse)

# Für EV (+ PV, +BS)
if 'EV' in selection:
    if 'Batteriespeicher' in selection:
        df_evbs, df_ohne = berechnen_ev.mit_hems_bs(df.copy(), pv, battery_capacity, homeoffice)
        ergebnisse = berechnen_ev.ersparnis_hems_bs(df_evbs, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'BS SOC', 'EV Ladung']
        df_plt = df_evbs.copy()
    else:
         df_b, df_ohne = berechnen_ev.mit_hems(df.copy(), pv, homeoffice)
         ergebnisse = berechnen_ev.ersparnis_hems(df_b, df_ohne, anlage_groesse, strompreis)
         plot_data = ['PV Ertrag', 'Strombedarf', 'überschuss', 'netzbezug', 'EV Ladung']
         df_plt = df_b.copy()

    berechnen_ev.print_ersparnis_hems_st(ergebnisse)

    # Für BS (+ PV)
else:
    df_pv = berechnen_bs.mit_pv(df.copy(), pv, anlage_groesse, battery_capacity)
    ergebnisse = berechnen_bs.ersparnis(df_pv, anlage_groesse, strompreis)
    plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug', 'BS SOC']
    df_plt = df_pv.copy()
    berechnen_bs.print_ersparnis_st(ergebnisse)

# Plots 
# maybe st.tabs für Diagramme
# Jahr - Summe pro Monat
# Monat - Summe pro Woche
# Woche - Summe pro Tag
# 1 Tag - pro Stunde
''
km = round(df_plt['ev distanz'].sum())
f'gefahrene km: {km}'
''
st.subheader("Plots", divider=True)

monat = st.selectbox(
    "Monat auswählen",
    (range(1, 13)))

f'## Tag: 1.{monat}'
tag = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
st.line_chart(tag)
''
f'## Drei Tage im Monat: {monat}'
woche = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-03 23:00:00', plot_data]
st.line_chart(woche)

'## Jahr'