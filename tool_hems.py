# In Terminal eingeben für remote deploy:
# streamlit run tool_hems.py --server.port 5996

import streamlit as st
import pandas as pd
import sys
import temperatur_aussen, try_region, lastprofile_VDI4655, heizkurve, pv_profil, berechnen_bs, berechnen_ev, berechnen_wp
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")

# Titel
st.title('Berechnungstool HEMS')
st.header('Wie viel kannst du mit HEMS einsparen?')

# Variable Abfrage
col1, col2 = st.columns(2)

with col1:
    ':blue[Haus Information:]'
    plz = st.text_input('Postleitzahl', placeholder = 'PLZ')
    flaeche = st.number_input(
    "Wohnfläche", value=None, placeholder="in m²"
    )
    baujahr = st.selectbox(
    "Baujahr",
    ("Vor 1918", "1919 - 1948", "1949 - 1957", "1958 - 1968", "1969 - 1978", "1979 - 1983", "1984 - 1994", "1995 - 2001", "Nach 2002", "KfW 85", "KfW 70", "KfW 55", "KfW 40", "Passivhaus"), placeholder="Bitte auswählen...")
    anzahl_personen = st.number_input("Hausbewohner", value=0, placeholder="Anzahl")
    strombedarf = st.number_input("Strombedarf", value = None, placeholder ='in kWh')
    strompreis = st.number_input('Strompreis', value=None, placeholder = 'in Cent')

with col2:
   ':blue[Komponenten Auswahl: ]'
   anlage_groesse = st.number_input("PV Anlage",  value = None, placeholder = 'Größe in kWp')
   komponenten = ["Batteriespeicher", "Elektroauto", "Wärmepumpe"]
   selection = st.multiselect("Komponenten", komponenten, placeholder="Bitte auswählen...")
   if "Batteriespeicher" in selection:
        battery_capacity = st.number_input("Batteriespeicher", value = None, placeholder = 'Kapazität in kWh')
   if "Elektroauto" in selection:
        homeoffice = st.selectbox("Homeoffice", (True, False))
   if "Wärmepumpe" in selection:
        heizung = st.selectbox("Heizung", ("Heizkörper", "Fußbodenheizung"))

# Lastprofile für Strom, Heizung, PV und T_ausssen generieren
h, w, twe, s = lastprofile_VDI4655.get_jahresenergiebedarf(baujahr, float(flaeche), anzahl_personen, strombedarf)
TRY_region, T_n_aussen = try_region.get_try_t_n_aussen(int(plz))
df = lastprofile_VDI4655.get_lastprofile(w, s, twe, float(flaeche), TRY_region, anzahl_personen)
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

    if "Batteriespeicher" in selection and "Elektroauto" in selection:
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
    elif "Elektroauto" in selection:
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
    
    berechnen_wp.print_ersparnis_hems_st(ergebnisse)
    
    # Für EV (+ PV, +BS)
elif 'Elektroauto' in selection:
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

    berechnen_ev.print_ersparnis_hems_st(ergebnisse)

    # Für BS (+ PV)
else:
    df_pv = berechnen_bs.mit_pv(df.copy(), pv, anlage_groesse, battery_capacity)
    ergebnisse = berechnen_bs.ersparnis(df_pv, anlage_groesse, strompreis)
    plot_data = ['PV Ertrag', 'Strombedarf', 'netzeinspeisung', 'netzbezug']
    plot_data_2 = ['BS %']
    df_plt = df_pv.copy()
    berechnen_bs.print_ersparnis_st(ergebnisse)
''

if 'Elektroauto' in selection:
    km = round(df_plt['ev distanz'].sum())
    'Annahmen:'
    f'- Elektroauto wird {km} km gefahren.'
    '- Elektroauto wird nur zuhause geladen.'

''
## PLOTS ##
if 'Elektroauto' not in selection and 'Wärmepumpe' not in selection:
    ' ' # für nur BS keine Plots
else:
    st.subheader("Plots", divider=True)
    monat = st.selectbox(
    "Monat auswählen",
    (range(1, 13)))

    ## TAG ##
    f'## Tag: 1.{monat}'
    col1, col2 = st.columns(2)
    with col1:
        'Mit HEMS'
        tag_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
        tag_2 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]*100
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        for col in plot_data:
            fig.add_trace(
                go.Scatter(
                x=tag_1.index, 
                y=tag_1[col], 
                name=col, 
                fill='tozeroy',  # Füllt die Fläche unter der Linie
                mode='lines',
                line=dict(width=1.5)  # Linienbreite anpassen
            ),
            secondary_y=False,)
        for col in plot_data_2:
            fig.add_trace(
                go.Scatter(x=tag_2.index, y=tag_2[col], name=col, line=dict(dash='dot')),
                secondary_y=True,
            ) 
        
        fig.update_xaxes(title_text="Zeit")

        # Set y-axes titles
        fig.update_yaxes(title_text="kWh", secondary_y=False)
        fig.update_yaxes(title_text="SOC %", secondary_y=True)


        # Update layout to move legend below the graph
        fig.update_layout(
            legend=dict(
                orientation="h",  # Horizontal alignment
                yanchor="top",
                y=-0.2,  # Move legend below the graph
                xanchor="center",
                x=0.5  # Center the legend
            )
        )
        st.plotly_chart(fig)

    with col2:
        ' Ohne HEMS'
        tag_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
        tag_2 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]*100
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        for col in plot_data:
            fig.add_trace(
                go.Scatter(
                    x=tag_1.index, 
                    y=tag_1[col], 
                    name=col, 
                    fill='tozeroy',  # Füllt die Fläche unter der Linie
                    mode='lines',
                    line=dict(width=1.5)  # Linienbreite anpassen
                ),
                secondary_y=False,
            )
        for col in plot_data_2:
            fig.add_trace(
                go.Scatter(x=tag_2.index, y=tag_2[col], name=col, line=dict(dash='dot')),
                secondary_y=True,
            ) 
        
        fig.update_xaxes(title_text="Zeit")

        # Set y-axes titles
        fig.update_yaxes(title_text="kWh", secondary_y=False)
        fig.update_yaxes(title_text="SOC %", secondary_y=True)


        # Update layout to move legend below the graph
        fig.update_layout(
            legend=dict(
                orientation="h",  # Horizontal alignment
                yanchor="top",
                y=-0.2,  # Move legend below the graph
                xanchor="center",
                x=0.5  # Center the legend
            )
        )
        st.plotly_chart(fig)

    ## WOCHE ##
    f'## 1. Woche im Monat: {monat}'
    'Mit HEMS'
    woche_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
    woche_2 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data_2]*100
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for col in plot_data:
        fig.add_trace(
            go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
                mode='lines',
                line=dict(width=1.5)),
            secondary_y=False,
        )
    for col in plot_data_2:
        fig.add_trace(
            go.Scatter(x=woche_2.index, y=woche_2[col], name=col, line=dict(dash='dot')),
            secondary_y=True,
        ) 

    fig.update_xaxes(title_text="Zeit")

    # Set y-axes titles
    fig.update_yaxes(title_text="kWh", secondary_y=False)
    fig.update_yaxes(title_text="SOC %", secondary_y=True)


    # Update layout to move legend below the graph
    fig.update_layout(
        legend=dict(
            orientation="h",  # Horizontal alignment
            yanchor="top",
            y=-0.2,  # Move legend below the graph
            xanchor="center",
            x=0.5  # Center the legend
        )
    )
    st.plotly_chart(fig)
    ''
    'Ohne HEMS'
    woche_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
    woche_2 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data_2]*100
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for col in plot_data:
        fig.add_trace(
            go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
                mode='lines',
                line=dict(width=1.5)),
            secondary_y=False,
        )
    for col in plot_data_2:
        fig.add_trace(
            go.Scatter(x=woche_2.index, y=woche_2[col], name=col, line=dict(dash='dot')),
            secondary_y=True,
        ) 

    fig.update_xaxes(title_text="Zeit")

    # Set y-axes titles
    fig.update_yaxes(title_text="kWh", secondary_y=False)
    fig.update_yaxes(title_text="SOC %", secondary_y=True)


    # Update layout to move legend below the graph
    fig.update_layout(
        legend=dict(
            orientation="h",  # Horizontal alignment
            yanchor="top",
            y=-0.2,  # Move legend below the graph
            xanchor="center",
            x=0.5  # Center the legend
        )
    )
    st.plotly_chart(fig)
    ''
    '## Einsparung pro Woche im Jahr'
    # Einsparung pro Woche
    # Stromkosten
    df_plt['Stromkosten'] = df_plt['netzbezug']*strompreis
    df_ohne['Stromkosten'] = df_ohne['netzbezug']*strompreis
    # Einspeisevergütung 
    if anlage_groesse <= 10:
            einspeiseverguetung = 0.0796
    else:
            einspeiseverguetung = 0.0689 
    df_plt['Einspeisevergütung'] = df_plt['einspeisung'] * einspeiseverguetung
    df_ohne['Einspeisevergütung'] = df_ohne['einspeisung'] * einspeiseverguetung
    # Einsparung
    df_plt['Einsparung'] = (df_ohne['Stromkosten'] - df_ohne['Einspeisevergütung']) - (df_plt['Stromkosten']-df_plt['Einspeisevergütung'])

    # Kalenderwoche aus dem Zeitindex extrahieren
    df_plt['KW'] = df_plt.index.to_series().dt.isocalendar().week

    # Einsparung pro Kalenderwoche aggregieren (Summe der Stundenwerte pro KW)
    df_kw = df_plt.groupby('KW')['Einsparung'].sum().round(2).reset_index()

    # Erstelle das Balkendiagramm mit Plotly Express
    fig = px.bar(df_kw, x="KW", y="Einsparung", text=df_kw['Einsparung'].apply(lambda x: f"{x:.2f}"), 
                labels={"KW": "Kalenderwoche", "Einsparung": "Einsparung (€)"})

    fig.update_traces(textposition='outside')

    # Layout-Anpassungen
    fig.update_layout(xaxis=dict(tickmode="linear"))

    # Diagramm anzeigen
    st.plotly_chart(fig)