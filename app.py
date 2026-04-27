import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests

st.set_page_config(page_title="Logística Rubiales - Clústeres", layout="wide")

# 1. Conversión DMS a Decimal
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

# 2. Función para obtener la geometría de la carretera
def obtener_ruta_real(puntos):
    if len(puntos) < 2: return []
    coords_url = ";".join([f"{p['lon']},{p['lat']}" for p in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            return [[coord[1], coord[0]] for coord in data['routes'][0]['geometry']['coordinates']]
    except:
        pass
    return []

@st.cache_data
def cargar_base_coordenadas(file_path):
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    # Agrupamos por Clúster para mostrar el nombre del cluster y la lista de pozos que contiene
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('Clúster').agg({
        'lat_dec': 'first', 
        'lon_dec': 'first', 
        'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("📍 Planificador de Rutas por Clúster: Rubiales")

try:
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    st.sidebar.header("Logística de Movilización")
    ruta_input = st.sidebar.text_area("Pega aquí los nombres de los Clústeres:", placeholder="RB-162\nRB-119")
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for nombre in nombres_ruta:
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({
                'nombre': nombre, # Aquí guardamos el nombre del CLÚSTER
                'lat': match.iloc[0]['lat_dec'], 
                'lon': match.iloc[0]['lon_dec'], 
                'pozos': match.iloc[0]['POZO']
            })

    # Centro del mapa
    m = folium.Map(location=[df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()], zoom_start=12, tiles="OpenStreetMap")

    if puntos_ruta:
        geometria_carretera = obtener_ruta_real(puntos_ruta)
        
        if geometria_carretera:
            folium.PolyLine(geometria_carretera, color="#2E86C1", weight=5, opacity=0.8).add_to(m)
            # Conectores punteados
            folium.PolyLine([[puntos_ruta[0]['lat'], puntos_ruta[0]['lon']], geometria_carretera[0]], color="#2E86C1", weight=2, dash_array='5').add_to(m)
            folium.PolyLine([[puntos_ruta[-1]['lat'], puntos_ruta[-1]['lon']], geometria_carretera[-1]], color="#2E86C1", weight=2, dash_array='5').add_to(m)

        # Marcadores con el icono de cabezal (Arbolito de Navidad)
        for i, p in enumerate(puntos_ruta):
            color_well = 'darkblue' if i == 0 else ('darkred' if i == len(puntos_ruta)-1 else 'cadetblue')
            
            folium.Marker(
                location=[p['lat'], p['lon']],
                # El popup muestra primero el nombre del CLÚSTER
                popup=folium.Popup(f"<b>CLÚSTER: {p['nombre']}</b><br>Contiene pozos: {p['pozos']}", max_width=250),
                tooltip=f"Clúster {p['nombre']}",
                # Usamos el icono 'oil-well' que se parece mucho a la estructura que enviaste
                icon=folium.Icon(color=color_well, icon='oil-well', prefix='fa')
            ).add_to(m)
            
        st.success(f"Ruta generada conectando {len(puntos_ruta)} Clústeres.")

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
