import pandas as pd
import folium
from streamlit_folium import st_folium
import re

# Función para convertir el formato "3° 49' 6.105" N" a decimal
def dms_to_decimal(dms_str):
    if pd.isna(dms_str): return None
    # Extraer números usando expresiones regulares
    parts = re.findall(r"[-+]?\d*\.\d+|\d+", dms_str)
    deg, minu, sec = map(float, parts)
    decimal = deg + (minu / 60) + (sec / 3600)
    # Si es Sur o Oeste (W), el valor es negativo
    if 'S' in dms_str or 'W' in dms_str:
        decimal *= -1
    return decimal

# 1. Cargar el archivo (ajusta el nombre a tu archivo real)
# df = pd.read_excel("coordenadas_pozos.xlsx")

# 2. Procesar las columnas de tu imagen
# Supongamos que las columnas se llaman 'Latitud' y 'Longitud'
# df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
# df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)

# Visualización base
def generar_mapa(dataframe):
    # Centrar en Rubiales
    m = folium.Map(location=[3.8, -71.5], zoom_start=11, tiles="CartoDB positron")
    
    for _, row in dataframe.iterrows():
        # Lógica de notificación (puedes añadir condiciones según el nombre del cluster)
        color_icono = 'blue'
        popup_text = f"Pozo: {row['POZO']}<br>Cluster: {row['Clúster']}"
        
        if "restringido" in str(row.get('Notificacion', '')).lower():
            color_icono = 'orange'
            popup_text += f"<br>⚠️ {row['Notificacion']}"

        folium.Marker(
            location=[row['lat_dec'], row['lon_dec']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=row['POZO'],
            icon=folium.Icon(color=color_icono, icon='tint')
        ).add_to(m)
    
    return m
