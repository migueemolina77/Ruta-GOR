import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

# Configuración de página para evitar la pantalla negra
st.set_page_config(layout="wide")

def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str): return None
        # Limpieza para el formato de tu tabla: 3° 49' 6.105" N
        parts = re.findall(r"[-+]?\d*\.\d+|\d+", str(dms_str))
        deg, minu, sec = map(float, parts)
        decimal = deg + (minu / 60) + (sec / 3600)
        if 'S' in str(dms_str) or 'W' in str(dms_str):
            decimal *= -1
        return decimal
    except:
        return None

st.title("📍 Logística de Pozos: Rubiales & Caño Sur")

# Intenta cargar el archivo
try:
    # Cambia 'coordenadas.xlsx' por el nombre de tu archivo en GitHub
    df = pd.read_excel("coordenadas.xlsx") 
    
    # Aplicamos la conversión a tus columnas de la imagen
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    
    # Filtramos filas sin coordenadas para evitar que el mapa falle
    df = df.dropna(subset=['lat_dec', 'lon_dec'])

    if not df.empty:
        # Crear mapa centrado en el promedio de tus pozos
        m = folium.Map(location=[df['lat_dec'].mean(), df['lon_dec'].mean()], zoom_start=11)

        for _, row in df.iterrows():
            folium.Marker(
                location=[row['lat_dec'], row['lon_dec']],
                popup=f"Pozo: {row['POZO']} - Cluster: {row['Clúster']}",
                tooltip=row['POZO'],
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

        # Renderizar mapa
        st_folium(m, width=1000, height=600)
    else:
        st.error("No se encontraron coordenadas válidas en el archivo.")

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.info("Asegúrate de que el archivo Excel esté en la raíz de tu repositorio de GitHub.")
