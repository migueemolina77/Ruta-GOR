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
        if pd.isna(dms_str) or str(dms_str).strip() == "": return None
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

# 1. Cargar el archivo con el ajuste de cabecera
try:
    nombre_archivo = "Coordenadas Rubiales.xlsx"
    
    # MODIFICACIÓN: header=2 le indica que los títulos reales están en la fila 3 de Excel
    df = pd.read_excel(nombre_archivo, header=6)
    
    # Limpiamos nombres de columnas (quita espacios al inicio/final si los hay)
    df.columns = df.columns.astype(str).str.strip()
    
    # 2. Procesar coordenadas geográficas usando los nombres de tus columnas
    # Verificamos si las columnas existen antes de procesar
    if 'Latitud' in df.columns and 'Longitud' in df.columns:
        df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
        df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
        
        # Limpiar filas que no tengan coordenadas válidas
        df_clean = df.dropna(subset=['lat_dec', 'lon_dec'])

        if not df_clean.empty:
            # Crear el mapa centrado en el promedio de los pozos
            centro_lat = df_clean['lat_dec'].mean()
            centro_lon = df_clean['lon_dec'].mean()
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12)

            # 3. Agregar marcadores
            for _, row in df_clean.iterrows():
                # Nombres de columnas según tu imagen
                pozo = row.get('POZO', 'N/A')
                cluster = row.get('Clúster', 'N/A')
                
                info_pozo = f"<b>Pozo:</b> {pozo}<br><b>Cluster:</b> {cluster}"
                
                folium.Marker(
                    location=[row['lat_dec'], row['lon_dec']],
                    popup=folium.Popup(info_pozo, max_width=300),
                    tooltip=f"Ver {pozo}",
                    icon=folium.Icon(color='blue', icon='tint')
                ).add_to(m)

            # 4. Mostrar el mapa
            st_folium(m, width=1100, height=600)
            st.success(f"Se han cargado {len(df_clean)} puntos correctamente.")
        else:
            st.error("No se pudieron convertir las coordenadas. Revisa que el formato sea '3° 49\' 6.105\" N'")
    else:
        st.error("No se encontraron las columnas 'Latitud' o 'Longitud'.")
        # Esto ayuda a diagnosticar qué nombres está leyendo Python realmente
        st.write("Columnas detectadas en el archivo:", list(df.columns))

except FileNotFoundError:
    st.error(f"No se encontró el archivo: '{nombre_archivo}'.")
except Exception as e:
    st.error(f"Ocurrió un error inesperado: {e}")
