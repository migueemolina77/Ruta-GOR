import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

# Configuración de la página
st.set_page_config(page_title="Logística Rubiales & Caño Sur", layout="wide")

# Función para convertir coordenadas de tu tabla (3° 49' 6.105" N) a decimal
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or dms_str == "": return None
        # Extraer los números de la cadena de texto
        parts = re.findall(r"[-+]?\d*\.\d+|\d+", str(dms_str))
        if len(parts) < 3: return None
        
        deg, minu, sec = map(float, parts)
        decimal = deg + (minu / 60) + (sec / 3600)
        
        # Si es Sur (S) u Oeste (W/O), el valor debe ser negativo
        if any(char in str(dms_str).upper() for char in ['S', 'W', 'O']):
            decimal *= -1
        return decimal
    except Exception:
        return None

st.title("📍 Mapa de Movilización: Rubiales & Caño Sur")
st.markdown("Visualización de clusters y alertas de vía para operaciones de subsuelo.")

# 1. Cargar el archivo con el nombre exacto que me indicaste
try:
    nombre_archivo = "Coordenadas Rubiales.xlsx"
    df = pd.read_excel(nombre_archivo)
    
    # 2. Procesar coordenadas geográficas usando los nombres de tus columnas
    # Usamos la columna 'Latitud' y 'Longitud' del Datum Bogotá (Arenas) de tu imagen
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    
    # Limpiar filas que no tengan coordenadas válidas
    df_clean = df.dropna(subset=['lat_dec', 'lon_dec'])

    if not df_clean.empty:
        # Crear el mapa centrado en el promedio de los pozos de Rubiales
        centro_lat = df_clean['lat_dec'].mean()
        centro_lon = df_clean['lon_dec'].mean()
        m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles="OpenStreetMap")

        # 3. Agregar marcadores para cada Pozo/Cluster
        for _, row in df_clean.iterrows():
            # Texto que aparecerá al hacer clic
            info_pozo = f"""
            <b>Pozo:</b> {row['POZO']}<br>
            <b>Cluster:</b> {row['Clúster']}<br>
            """
            
            folium.Marker(
                location=[row['lat_dec'], row['lon_dec']],
                popup=folium.Popup(info_pozo, max_width=300),
                tooltip=f"Ver {row['POZO']}",
                icon=folium.Icon(color='blue', icon='tint')
            ).add_to(m)

        # 4. Mostrar el mapa en Streamlit
        st_folium(m, width=1100, height=600)
        
        st.success(f"Se han cargado {len(df_clean)} puntos correctamente.")
        
    else:
        st.error("No se pudieron convertir las coordenadas. Revisa el formato de latitud/longitud.")

except FileNotFoundError:
    st.error(f"No se encontró el archivo: '{nombre_archivo}'.")
    st.info("Asegúrate de que el archivo Excel esté subido a GitHub con ese nombre exacto (incluyendo espacios).")
except Exception as e:
    st.error(f"Ocurrió un error inesperado: {e}")
