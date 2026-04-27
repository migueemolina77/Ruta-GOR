import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

# Configuración de la página
st.set_page_config(page_title="Logística Rubiales - Navegación", layout="wide")

# 1. Función de conversión de coordenadas (DMS a Decimal)
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or str(dms_str).strip() == "": return None
        parts = re.findall(r"[-+]?\d*\.\d+|\d+", str(dms_str))
        if len(parts) < 3: return None
        deg, minu, sec = map(float, parts)
        decimal = deg + (minu / 60) + (sec / 3600)
        if any(char in str(dms_str).upper() for char in ['S', 'W', 'O']):
            decimal *= -1
        return decimal
    except:
        return None

# 2. Carga de datos optimizada con filtrado de NaNs
@st.cache_data
def cargar_base_coordenadas(file_path):
    # Leemos desde la fila 7 del Excel
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    
    # Procesamos las coordenadas
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    
    # FILTRO CRÍTICO: Eliminamos filas que no tengan coordenadas para evitar el error de NaNs
    df_validos = df.dropna(subset=['lat_dec', 'lon_dec'])
    
    # Agrupamos por Clúster para tener puntos únicos y limpios
    df_geo = df_validos.groupby('Clúster').agg({
        'lat_dec': 'first',
        'lon_dec': 'first',
        'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()
    
    return df_geo

st.title("📍 Planificador de Rutas: Rubiales & Caño Sur")

try:
    # Cargar la base maestra
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    # BARRA LATERAL: Entrada de ruta
    st.sidebar.header("Planificación de Movilización")
    ruta_input = st.sidebar.text_area(
        "Pega aquí la secuencia de Clústeres:",
        placeholder="Ejemplo:\nRB-162\nRB-119\nRB-1",
        help="El mapa conectará los clústeres en el orden en que los ingreses."
    )

    # Procesar nombres de la ruta ingresada
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for nombre in nombres_ruta:
        # Búsqueda exacta del nombre del clúster
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        
        if not match.empty:
            lat = match.iloc[0]['lat_dec']
            lon = match.iloc[0]['lon_dec']
            
            # Verificación final de que la coordenada sea un número válido
            if pd
