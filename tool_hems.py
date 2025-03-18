# In Terminal eingeben für remote deploy:
# streamlit run tool_hems.py --server.port 5996

import streamlit as st
import pandas as pd
import temperatur_aussen, try_region, lastprofile_VDI4655, heizkurve, pv_profil, berechnen_bs, berechnen_ev, berechnen_wp
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")

# Titel
st.title('Berechnungstool HEMS')
st.header('Wie viel kannst du mit HEMS einsparen?')
'Bitte alle Felder ausfüllen und dann "BERECHNEN" klicken.'

# INPUTS 
# Variable Abfrage
col1, col2 = st.columns(2)

with col1:
    ':blue[Haus Information:]'
    plz = st.text_input('Postleitzahl')
    flaeche = st.number_input(
    "Wohnfläche", value=None, placeholder="in m²"
    )
    baujahr = st.selectbox(
    "Baujahr",
    ("Vor 1918", "1919 - 1948", "1949 - 1957", "1958 - 1968", "1969 - 1978", "1979 - 1983", "1984 - 1994", "1995 - 2001", "Nach 2002", "KfW 85", "KfW 70", "KfW 55", "KfW 40", "Passivhaus"))
    anzahl_personen = st.number_input("Hausbewohner", value=0, placeholder="Anzahl")
    strombedarf = st.number_input("Strombedarf (wenn unbekannt 0 eingeben)", value = None, placeholder ='in kWh')
    strompreis = st.number_input('Strompreis', value=None, placeholder = 'in Cent')

with col2:
   ':blue[Komponenten Auswahl: ]'
   anlage_groesse = st.number_input("PV Anlage",  value = None, placeholder = 'Größe in kWp')
   komponenten = ["Batteriespeicher", "EV", "Wärmepumpe"]
   selection = st.multiselect("Komponenten", komponenten)
   if "Batteriespeicher" in selection:
        battery_capacity = st.number_input("Batteriespeicher", value = None, placeholder = 'Kapazität in kWh')
   if "EV" in selection:
        homeoffice = st.selectbox("Homeoffice (True = 3 Tage; False = 0 Tage)", (True, False))
   if "Wärmepumpe" in selection:
        heizung = st.selectbox("Heizung", ("Heizkörper", "Fußbodenheizung"))

col1, col2, col3 , col4, col5, col6, col7 = st.columns(7)
with col1:
    pass
with col2:
    pass
with col4:
    pass
with col5:
    pass
with col6:
    pass
with col7:
    pass
with col4 :
    berechnen = st.button('BERECHNEN')

':blue[!! Nach Änderungen in den oberen Feldern bitte erneut auf "BERECHNEN" klicken !!]'

# Für WP (+ PV, + BS, + LS)
if berechnen:
    st.session_state.df_plt = []
    st.session_state.df_ohne = []
    st.session_state.plot_data = []
    st.session_state.plot_data_2 = []
    st.session_state.ergebnisse = []

    # Lastprofile für Strom, Heizung, PV und T_ausssen generieren
    h, w, twe, s = lastprofile_VDI4655.get_jahresenergiebedarf(baujahr, float(flaeche), anzahl_personen, strombedarf)
    TRY_region, T_n_aussen = try_region.get_try_t_n_aussen(int(plz))
    df = lastprofile_VDI4655.get_lastprofile(w, s, twe, float(flaeche), TRY_region, anzahl_personen)
    df['T_aussen'] = temperatur_aussen.get_hourly_temperature(plz, 2014)
    pv = pv_profil.get_pv_profil(plz, 2014, anlage_groesse)
    strompreis = strompreis/100

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

        if "Batteriespeicher" in selection and "EV" in selection:
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
            plot_data_2 = []

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

        # Für BS (+ PV)
    else:
        df_pv = berechnen_bs.mit_pv(df.copy(), pv, anlage_groesse, battery_capacity)
        ergebnisse = berechnen_bs.ersparnis(df_pv, anlage_groesse, strompreis)
        plot_data = ['PV Ertrag', 'Strombedarf', 'netzeinspeisung', 'netzbezug']
        plot_data_2 = ['BS %']
        df_plt = df_pv.copy()
        df_ohne = df
        berechnen_bs.print_ersparnis_st(ergebnisse)
    ''
    st.session_state.df_plt = df_plt
    st.session_state.df_ohne = df_ohne
    st.session_state.plot_data = plot_data
    st.session_state.plot_data_2 = plot_data_2
    st.session_state.ergebnisse = ergebnisse

if "df_plt" in st.session_state and "df_ohne" in st.session_state:
    ergebnisse = st.session_state.ergebnisse

    if "Wärmepumpe" in selection:
        berechnen_wp.print_ersparnis_hems_st(ergebnisse)
    elif "EV" in selection:
        berechnen_ev.print_ersparnis_hems_st(ergebnisse)
    elif "Batteriespeicher" in selection:
        berechnen_bs.print_ersparnis_st(ergebnisse)
else:
        st.error("Bitte zuerst auf 'BERECHNEN' klicken, um die Ergebnisse zu berechnen.")


if 'EV' in selection and "df_plt" in st.session_state:
    km = round(st.session_state.df_plt['ev distanz'].sum())
    'Annahmen:'
    f'- Elektroauto wird {km} km gefahren.'
    '- Elektroauto wird nur zuhause geladen.'
    ''

# Diagramm Einsparung pro KW
if "df_plt" in st.session_state and "df_ohne" in st.session_state:
    df_plt = st.session_state.df_plt
    df_ohne = st.session_state.df_ohne

    if 'EV' not in selection and 'Wärmepumpe' not in selection:
            ''
    else:
        st.subheader("Einsparung pro Woche im Jahr", divider=True)
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
        fig.update_layout(xaxis=dict(tickmode="linear"))

        # Diagramm anzeigen
        st.plotly_chart(fig)

# DIAGRAMME 
if "df_plt" in st.session_state and "df_ohne" in st.session_state:
    df_plt = st.session_state.df_plt
    df_ohne = st.session_state.df_ohne
    plot_data = st.session_state.plot_data
    plot_data_2 = st.session_state.plot_data_2

    if 'EV' not in selection and 'Wärmepumpe' not in selection:
            'Es werden keine Diagramme bei der Auswahl: PV + Batteriespeicher erstellt.' # für nur BS keine Plots
    
    elif 'EV' not in selection and 'Batteriespeicher' not in selection: # Nur WP
        st.subheader("Diagramme", divider=True)
        "Wählen Sie einen Monat aus und klicken auf 'Diagramme erstellen'. Die Monatsauswahl kann jederzeit geändert werden."
        monat = st.selectbox(
            "Monat auswählen:",
            (range(1, 13)))

        plots = st.button('Diagramme erstellen')
        
        if plots:
            ## TAG ##
            f'## Tag: 1.{monat}'
            col1, col2 = st.columns(2)
            with col1:
                '#### Mit HEMS'
                tag_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
                fig = make_subplots()
        
                for col in plot_data:
                    fig.add_trace(
                        go.Scatter(
                            x=tag_1.index, 
                            y=tag_1[col], 
                            name=col, 
                            fill='tozeroy',  # Füllt die Fläche unter der Linie
                            mode='lines',
                            line=dict(width=1.5)  # Linienbreite anpassen
                        )
                    )
                
                fig.update_xaxes(title_text="Zeit")
                fig.update_yaxes(title_text="kWh")

                fig.update_layout(
                    legend=dict(
                        orientation="h",  
                        yanchor="top",
                        y=-0.2,  
                        xanchor="center",
                        x=0.5 
                    )
                )
                st.plotly_chart(fig)

            with col2:
                '#### Ohne HEMS'
                tag_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
                fig = make_subplots()
                
                for col in plot_data:
                    fig.add_trace(
                        go.Scatter(
                            x=tag_1.index, 
                            y=tag_1[col], 
                            name=col, 
                            fill='tozeroy',  
                            mode='lines',
                            line=dict(width=1.5)  
                        )
                    )
                
                fig.update_xaxes(title_text="Zeit")
                fig.update_yaxes(title_text="kWh")

                fig.update_layout(
                    legend=dict(
                        orientation="h",  
                        yanchor="top",
                        y=-0.2, 
                        xanchor="center",
                        x=0.5  
                    )
                )
                st.plotly_chart(fig)

            ## WOCHE ##
            f'## 1. Woche im Monat: {monat}'
            '#### Mit HEMS'
            woche_1 = df_plt.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
            fig = make_subplots()

            for col in plot_data:
                fig.add_trace(
                    go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
                        mode='lines',
                        line=dict(width=1.5))
                )

            fig.update_xaxes(title_text="Zeit")
            fig.update_yaxes(title_text="kWh")

            fig.update_layout(
                legend=dict(
                    orientation="h",  
                    yanchor="top",
                    y=-0.2,  
                    xanchor="center",
                    x=0.5  
                )
            )
            st.plotly_chart(fig)
            ''
            '#### Ohne HEMS'
            woche_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-07 23:00:00', plot_data]
            fig = make_subplots()

            for col in plot_data:
                fig.add_trace(
                    go.Scatter(x=woche_1.index, y=woche_1[col], name=col, fill='tozeroy', 
                        mode='lines',
                        line=dict(width=1.5))
                )

            fig.update_xaxes(title_text="Zeit")
            fig.update_yaxes(title_text="kWh", secondary_y=False)

            fig.update_layout(
                legend=dict(
                    orientation="h",  
                    yanchor="top",
                    y=-0.2,  
                    xanchor="center",
                    x=0.5  
                )
            )
            st.plotly_chart(fig)
    else: 
        st.subheader("Diagramme", divider=True)
        "Wählen Sie einen Monat aus und klicken auf 'Diagramme erstellen'. Die Monatsauswahl kann jederzeit geändert werden."
        monat = st.selectbox(
            "Monat auswählen:",
            (range(1, 13)))

        plots = st.button('Diagramme erstellen')
        
        if plots:
                ## TAG ##
                f'## Tag: 1.{monat}'
                col1, col2 = st.columns(2)
                with col1:
                    '#### Mit HEMS'
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
                    fig.update_yaxes(title_text="kWh", secondary_y=False)
                    fig.update_yaxes(title_text="SOC %", secondary_y=True)

                    fig.update_layout(
                        legend=dict(
                            orientation="h",  
                            yanchor="top",
                            y=-0.2,  
                            xanchor="center",
                            x=0.5 
                        )
                    )
                    st.plotly_chart(fig)

                with col2:
                    '####  Ohne HEMS'
                    tag_1 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data]
                    tag_2 = df_ohne.loc[f'2014-{monat:02d}-01 00:00:00':f'2014-{monat:02d}-01 23:00:00', plot_data_2]*100
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    for col in plot_data:
                        fig.add_trace(
                            go.Scatter(
                                x=tag_1.index, 
                                y=tag_1[col], 
                                name=col, 
                                fill='tozeroy',  
                                mode='lines',
                                line=dict(width=1.5)  
                            ),
                            secondary_y=False,
                        )
                    for col in plot_data_2:
                        fig.add_trace(
                            go.Scatter(x=tag_2.index, y=tag_2[col], name=col, line=dict(dash='dot')),
                            secondary_y=True,
                        ) 
                    
                    fig.update_xaxes(title_text="Zeit")
                    fig.update_yaxes(title_text="kWh", secondary_y=False)
                    fig.update_yaxes(title_text="SOC %", secondary_y=True)

                    fig.update_layout(
                        legend=dict(
                            orientation="h",  
                            yanchor="top",
                            y=-0.2, 
                            xanchor="center",
                            x=0.5  
                        )
                    )
                    st.plotly_chart(fig)

                ## WOCHE ##
                f'## 1. Woche im Monat: {monat}'
                '#### Mit HEMS'
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
                fig.update_yaxes(title_text="kWh", secondary_y=False)
                fig.update_yaxes(title_text="SOC %", secondary_y=True)

                fig.update_layout(
                    legend=dict(
                        orientation="h",  
                        yanchor="top",
                        y=-0.2,  
                        xanchor="center",
                        x=0.5  
                    )
                )
                st.plotly_chart(fig)
                ''
                '#### Ohne HEMS'
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
                fig.update_yaxes(title_text="kWh", secondary_y=False)
                fig.update_yaxes(title_text="SOC %", secondary_y=True)

                fig.update_layout(
                    legend=dict(
                        orientation="h",  
                        yanchor="top",
                        y=-0.2,  
                        xanchor="center",
                        x=0.5  
                    )
                )
                st.plotly_chart(fig)