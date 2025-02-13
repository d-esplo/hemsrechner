import pandas as pd
import temperatur_aussen, try_region, lastprofile_VDI4655, heizkurve, pv_profil, berechnen_bs, berechnen_ev, berechnen_wp
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Strompreis
strompreis = 0.358

plz = 40599
flaeche = 200
# Baujahr Auswahl "Vor 1918", "1919 - 1948", "1949 - 1957", "1958 - 1968", "1969 - 1978", "1979 - 1983", "1984 - 1994", "1995 - 2001", "Nach 2002", "KfW 85", "KfW 70", "KfW 55", "KfW 40", "Passivhaus")
baujahr = "1984 - 1994"
anzahl_personen = 3
strombedarf = 4000
strompreis = 35.8

anlage_groesse = 10
# Auswahl: ["Batteriespeicher", "EV", "Wärmepumpe"]
selection = ["Batteriespeicher", "EV", "Wärmepumpe"]
battery_capacity = 10
homeoffice = True
# Auswahl: ("Heizkörper", "Fußbodenheizung")
heizung = "Heizkörper"


# Lastprofile für Strom, Heizung, PV und T_ausssen generieren
h, w, twe, s = lastprofile_VDI4655.get_jahresenergiebedarf(baujahr, flaeche, anzahl_personen, strombedarf)
TRY_region, T_n_aussen = try_region.get_try_t_n_aussen(int(plz))
df = lastprofile_VDI4655.get_lastprofile(w, s, twe, flaeche, TRY_region, anzahl_personen)
df['T_aussen'] = temperatur_aussen.get_hourly_temperature(plz, 2014)
pv = pv_profil.get_pv_profil(plz, 2014, anlage_groesse)
strompreis = strompreis/100

# Für WP (+ PV, + BS, + LS)
if "Wärmepumpe" in selection:

    # WP, Heizleistung, Heizkurve
    hz, T_soll, T_n_vor, T_n_rueck = heizkurve.get_heizkurve(heizung, df['T_aussen'], T_n_aussen)
    df['T_vor'] = hz['T_vor']
    wp_groesse, wp_modell = berechnen_wp.get_waermepumpe(h)
    df = heizkurve.get_cop(wp_groesse, df)
    df = berechnen_wp.get_max_heizleistung(wp_groesse, df)
    V_ps, PS_verlust, Q_ps, Q_ps_max, Q_ps_ueber = berechnen_wp.get_pufferspeicher(h, T_n_vor, T_n_rueck)
    
    # Basis Programm - ohne PV
    df, df_ohne = berechnen_wp.mit_hems(df, pv, Q_ps, Q_ps_max, Q_ps_ueber, PS_verlust)

    if "Batteriespeicher" and "EV" in selection:
        df, df_ohne = berechnen_wp.mit_hems_bsev(df, df_ohne, pv, battery_capacity, anlage_groesse, homeoffice)
        ergebnisse = berechnen_wp.ersparnis_hems_bsev(df, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug', 'Strombedarf WP']
        plot_data_2 = ['EV %', 'BS %']
        df_plt = df.copy()
    elif "Batteriespeicher" in selection:
        df, df_ohne = berechnen_wp.mit_hems_bs(df, df_ohne, pv, battery_capacity, anlage_groesse)
        ergebnisse = berechnen_wp.ersparnis_hems_bs(df, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug', 'Strombedarf WP']  
        plot_data_2 = ['BS %']
        df_plt = df.copy()
    elif "EV" in selection:
        df, df_ohne = berechnen_wp.mit_hems_ev(df, df_ohne, pv, homeoffice)
        ergebnisse = berechnen_wp.ersparnis_hems_ev(df, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug', 'Strombedarf WP']
        plot_data_2 = ['EV %']
        df_plt = df.copy()
    else: 
        # nur WP & PV 
        ergebnisse = berechnen_wp.ersparnis_hems(df, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug', 'Strombedarf WP']
        df_plt = df.copy()
    
    berechnen_wp.print_ersparnis_hems(ergebnisse)
    
    # Für EV (+ PV, +BS)
elif 'EV' in selection:
    if 'Batteriespeicher' in selection:
        df_evbs, df_ohne = berechnen_ev.mit_hems_bs(df.copy(), pv, battery_capacity, homeoffice)
        ergebnisse = berechnen_ev.ersparnis_hems_bs(df_evbs, df_ohne, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug']
        plot_data_2 = ['EV %', 'BS %']
        df_plt = df_evbs.copy()
    else:
         df_b, df_ohne = berechnen_ev.mit_hems(df.copy(), pv, homeoffice)
         ergebnisse = berechnen_ev.ersparnis_hems(df_b, df_ohne, anlage_groesse, strompreis)
         plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug']
         plot_data_2 = ['EV %']
         df_plt = df_b.copy()

    berechnen_ev.print_ersparnis_hems(ergebnisse)

    # Für BS (+ PV)
else:
    df_pv = berechnen_bs.mit_pv(df.copy(), pv, anlage_groesse, battery_capacity)
    ergebnisse = berechnen_bs.ersparnis(df_pv, anlage_groesse, strompreis)
    plot_data = ['PV Ertrag', 'Strombedarf', 'einspeisung', 'netzbezug']
    plot_data_2 = ['BS %']
    df_plt = df_pv.copy()
    berechnen_bs.print_ersparnis(ergebnisse)

km = round(df_plt['ev distanz'].sum())
print('Annahmen:')
print(f'- EV wird {km} km gefahren.')
print('- EV wird nur zuhause geladen')
''
## PLOTS ##


# Monat Auswählen: 1-12
monat = 1

## TAG ##
print(f'Plot Tag: 1.{monat}')
print('Mit HEMS')
import matplotlib.pyplot as plt

# Daten für den gewünschten Monat extrahieren
tag_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
tag_2 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]

# Matplotlib Figure erstellen
fig, ax1 = plt.subplots(figsize=(10, 5))

# Zweite Achse für die sekundären Werte hinzufügen
ax2 = ax1.twinx()

# Primäre Achsen-Daten (SOLID FILLED AREAS)
lines_1 = []
labels_1 = []
#colors = ['blue', 'red', 'green', 'purple', 'orange']  # Customize colors for solid fills

for i, col in enumerate(plot_data):
    line, = ax1.plot(tag_1.index, tag_1[col], label=col, linewidth=1.5)
    ax1.fill_between(tag_1.index, tag_1[col], alpha=1.0)  # Solid Fill (no transparency)
    lines_1.append(line)
    labels_1.append(col)  # Labels für Legende speichern

# Sekundäre Achsen-Daten (Gestrichelte Linien)
lines_2 = []
labels_2 = []
for col in plot_data_2:
    line, = ax2.plot(tag_2.index, tag_2[col], linestyle="dashed", label=col)
    lines_2.append(line)
    labels_2.append(col)  # Labels für Legende speichern

# Achsenbeschriftungen
ax1.set_xlabel("Zeit")
ax1.set_ylabel("kWh", color="black")
ax2.set_ylabel("SOC %", color="black")

# **EXPLICITLY ADDING LEGENDS TO FIX THE MISSING ISSUE**
legend_1 = ax1.legend(handles=lines_1, labels=labels_1, loc="upper left", frameon=True)
legend_2 = ax2.legend(handles=lines_2, labels=labels_2, loc="upper right", frameon=True)

# Kombinierte Legende unten
fig.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=True)

# Layout-Anpassung für bessere Lesbarkeit
plt.xticks(rotation=45)
plt.tight_layout()

# Diagramm anzeigen
plt.show()





# tag_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
# tag_2 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]
# fig = make_subplots(specs=[[{"secondary_y": True}]])
    
# for col in plot_data:
#     fig.add_trace(
#         go.Scatter(
#         x=tag_1.index, 
#         y=tag_1[col], 
#         name=col, 
#         fill='tozeroy',  # Füllt die Fläche unter der Linie
#         mode='lines',
#         line=dict(width=1.5)  # Linienbreite anpassen
#     ),
#     secondary_y=False,)
# for col in plot_data_2:
#     fig.add_trace(
#         go.Scatter(x=tag_2.index, y=tag_2[col], name=col, line=dict(dash='dot')),
#         secondary_y=True,
#     ) 

# fig.update_xaxes(title_text="Zeit")

# # Set y-axes titles
# fig.update_yaxes(title_text="kWh", secondary_y=False)
# fig.update_yaxes(title_text="SOC %", secondary_y=True)


# # Update layout to move legend below the graph
# fig.update_layout(
#     legend=dict(
#         orientation="h",  # Horizontal alignment
#         yanchor="top",
#         y=-0.2,  # Move legend below the graph
#         xanchor="center",
#         x=0.5  # Center the legend
#     )
# )

# fig.show()


# print('Ohne HEMS')
# tag_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
# tag_2 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]
# fig = make_subplots(specs=[[{"secondary_y": True}]])

# for col in plot_data:
#     fig.add_trace(
#         go.Scatter(
#             x=tag_1.index, 
#             y=tag_1[col], 
#             name=col, 
#             fill='tozeroy',  # Füllt die Fläche unter der Linie
#             mode='lines',
#             line=dict(width=1.5)  # Linienbreite anpassen
#         ),
#         secondary_y=False,
#     )
# for col in plot_data_2:
#     fig.add_trace(
#         go.Scatter(x=tag_2.index, y=tag_2[col], name=col, line=dict(dash='dot')),
#         secondary_y=True,
#     ) 

# fig.update_xaxes(title_text="Zeit")

# # Set y-axes titles
# fig.update_yaxes(title_text="kWh", secondary_y=False)
# fig.update_yaxes(title_text="SOC %", secondary_y=True)


# # Update layout to move legend below the graph
# fig.update_layout(
#     legend=dict(
#         orientation="h",  # Horizontal alignment
#         yanchor="top",
#         y=-0.2,  # Move legend below the graph
#         xanchor="center",
#         x=0.5  # Center the legend
#     )
# )
# fig.show()

# ## WOCHE ##
# print(f'## 1. Woche im Monat: {monat}')
# print('Mit HEMS')
# woche_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
# woche_2 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data_2]
# fig = make_subplots(specs=[[{"secondary_y": True}]])

# for col in plot_data:
#     fig.add_trace(
#         go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
#             mode='lines',
#             line=dict(width=1.5)),
#         secondary_y=False,
#     )
# for col in plot_data_2:
#     fig.add_trace(
#         go.Scatter(x=woche_2.index, y=woche_2[col], name=col, line=dict(dash='dot')),
#         secondary_y=True,
#     ) 

# fig.update_xaxes(title_text="Zeit")

# # Set y-axes titles
# fig.update_yaxes(title_text="kWh", secondary_y=False)
# fig.update_yaxes(title_text="SOC %", secondary_y=True)


# # Update layout to move legend below the graph
# fig.update_layout(
#     legend=dict(
#         orientation="h",  # Horizontal alignment
#         yanchor="top",
#         y=-0.2,  # Move legend below the graph
#         xanchor="center",
#         x=0.5  # Center the legend
#     )
# )
# fig.show()

# print('Ohne HEMS')
# woche_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
# woche_2 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data_2]
# fig = make_subplots(specs=[[{"secondary_y": True}]])

# for col in plot_data:
#     fig.add_trace(
#         go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
#             mode='lines',
#             line=dict(width=1.5)),
#         secondary_y=False,
#     )
# for col in plot_data_2:
#     fig.add_trace(
#         go.Scatter(x=woche_2.index, y=woche_2[col], name=col, line=dict(dash='dot')),
#         secondary_y=True,
#     ) 

# fig.update_xaxes(title_text="Zeit")

# # Set y-axes titles
# fig.update_yaxes(title_text="kWh", secondary_y=False)
# fig.update_yaxes(title_text="SOC %", secondary_y=True)


# # Update layout to move legend below the graph
# fig.update_layout(
#     legend=dict(
#         orientation="h",  # Horizontal alignment
#         yanchor="top",
#         y=-0.2,  # Move legend below the graph
#         xanchor="center",
#         x=0.5  # Center the legend
#     )
# )
# fig.show()
# ''
# print('## Einsparung pro Woche im Jahr')
# # Einsparung pro Woche
# # Stromkosten
# df_plt['Stromkosten'] = df_plt['netzbezug']*strompreis
# df_ohne['Stromkosten'] = df_ohne['netzbezug']*strompreis
# # Einspeisevergütung 
# if anlage_groesse <= 10:
#         einspeiseverguetung = 0.0796
# else:
#         einspeiseverguetung = 0.0689 
# df_plt['Einspeisevergütung'] = df_plt['einspeisung'] * einspeiseverguetung
# df_ohne['Einspeisevergütung'] = df_ohne['einspeisung'] * einspeiseverguetung
# # Einsparung
# df_plt['Einsparung'] = (df_ohne['Stromkosten'] - df_ohne['Einspeisevergütung']) - (df_plt['Stromkosten']-df_plt['Einspeisevergütung'])

# # Kalenderwoche aus dem Zeitindex extrahieren
# df_plt['KW'] = df_plt.index.to_series().dt.isocalendar().week

# # Einsparung pro Kalenderwoche aggregieren (Summe der Stundenwerte pro KW)
# df_kw = df_plt.groupby('KW')['Einsparung'].sum().round(2).reset_index()

# # Erstelle das Balkendiagramm mit Plotly Express
# fig = px.bar(df_kw, x="KW", y="Einsparung", text=df_kw['Einsparung'].apply(lambda x: f"{x:.2f}"), 
#              labels={"KW": "Kalenderwoche", "Einsparung": "Einsparung (€)"})

# fig.update_traces(textposition='outside')

# # Layout-Anpassungen
# fig.update_layout(xaxis=dict(tickmode="linear"))

# # Diagramm anzeigen
# fig.show()