import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests # Necesario para consultar el motor de rutas

st.set_page_config(page_title="Logística Rubiales - Rutas Reales", layout="wide")

# 1. Conversión DMS a Decimal (Se mantiene)
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

# 2. Función para obtener la geometría de la carretera (OSRM)
def obtener_ruta_real(puntos):
    if len(puntos) < 2: return []
    
    # Construir la URL para OSRM (formato: lon,lat;lon,lat)
    coords_url = ";".join([f"{p['lon']},{p['lat']}" for p in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            # OSRM devuelve [longitud, latitud], Folium necesita [latitud, longitud]
            linea_real = [[coord[1], coord[0]] for coord in data['routes'][0]['geometry']['coordinates']]
            return linea_real
    except Exception as e:
        st.warning(f"No se pudo calcular la ruta por carretera (usando línea recta): {e}")
    return []

# 3. Carga de datos (Se mantiene optimizada)
@st.cache_data
def cargar_base_coordenadas(file_path):
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    df_validos = df.dropna(subset=['lat_dec', 'lon_dec'])
    return df_validos.groupby('Clúster').agg({
        'lat_dec': 'first', 'lon_dec': 'first', 'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("🚜 Navegación por Carretera: Rubiales & Caño Sur")

try:
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    # Entrada de ruta en la barra lateral
    st.sidebar.header("Plan de Movilización")
    ruta_input = st.sidebar.text_area("Pega aquí los Clústeres:", placeholder="RB-162\nRB-119")
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for nombre in nombres_ruta:
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({'nombre': nombre, 'lat': match.iloc[0]['lat_dec'], 'lon': match.iloc[0]['lon_dec'], 'pozos': match.iloc[0]['POZO']})

    # Construcción del Mapa
    m = folium.Map(location=[df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()], zoom_start=12, tiles="OpenStreetMap")

    if puntos_ruta:
        # LLAMADA AL MOTOR DE RUTAS
        geometria_carretera = obtener_ruta_real(puntos_ruta)
        
        if geometria_carretera:
            # Dibujar la ruta siguiendo las vías
            folium.PolyLine(geometria_carretera, color="#1E8449", weight=6, opacity=0.8).add_to(m)
        else:
            # Respaldo: Línea recta si falla el servidor o no hay vía mapeada
            coords_recta = [[p['lat'], p['lon']] for p in puntos_ruta]
            folium.PolyLine(coords_recta, color="red", weight=4, dash_array='10', opacity=0.6).add_to(m)

        # Marcadores
        for i, p in enumerate(puntos_ruta):
            color = 'green' if i == 0 else ('red' if i == len(puntos_ruta)-1 else 'blue')
            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=f"<b>{p['nombre']}</b>",
                icon=folium.Icon(color=color, icon='truck', prefix='fa')
            ).add_to(m)
            
        st.success("Ruta calculada siguiendo la infraestructura vial disponible.")

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
