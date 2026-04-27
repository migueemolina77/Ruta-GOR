import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests

st.set_page_config(page_title="Logística Rubiales - Activos", layout="wide")

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
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('Clúster').agg({
        'lat_dec': 'first', 'lon_dec': 'first', 'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("🛢️ Ubicación de Activos y Rutas: Rubiales")

try:
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    st.sidebar.header("Plan de Movilización")
    ruta_input = st.sidebar.text_area("Lista de Clústeres (Destinos):", placeholder="RB-162\nRB-119")
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for nombre in nombres_ruta:
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({
                'nombre': nombre, 
                'lat': match.iloc[0]['lat_dec'], 
                'lon': match.iloc[0]['lon_dec'], 
                'pozos': match.iloc[0]['POZO']
            })

    # Centro del mapa basado en los datos
    m = folium.Map(location=[df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()], zoom_start=12, tiles="OpenStreetMap")

    if puntos_ruta:
        geometria_carretera = obtener_ruta_real(puntos_ruta)
        
        if geometria_carretera:
            # Dibujar la ruta principal
            folium.PolyLine(geometria_carretera, color="#2E86C1", weight=5, opacity=0.8).add_to(m)
            
            # Dibujar líneas de acceso (antenas) desde los extremos de la vía hacia los cabezales exactos
            folium.PolyLine([[puntos_ruta[0]['lat'], puntos_ruta[0]['lon']], geometria_carretera[0]], 
                            color="#2E86C1", weight=2, dash_array='5', opacity=0.7).add_to(m)
            
            folium.PolyLine([[puntos_ruta[-1]['lat'], puntos_ruta[-1]['lon']], geometria_carretera[-1]], 
                            color="#2E86C1", weight=2, dash_array='5', opacity=0.7).add_to(m)
        else:
            # Respaldo en línea recta
            folium.PolyLine([[p['lat'], p['lon']] for p in puntos_ruta], color="#E74C3C", weight=3, dash_array='10').add_to(m)

        # Colocar marcadores con icono de pozo en la ubicación real del Clúster
        for i, p in enumerate(puntos_ruta):
            # Identificar inicio y fin con colores, pero con el mismo icono de pozo
            color_well = 'darkblue' if i == 0 else ('darkred' if i == len(puntos_ruta)-1 else 'cadetblue')
            label_tipo = "ORIGEN" if i == 0 else ("DESTINO" if i == len(puntos_ruta)-1 else "PUNTO INTERMEDIO")
            
            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=folium.Popup(f"<b>{label_tipo}: {p['nombre']}</b><br>Pozos: {p['pozos']}", max_width=250),
                tooltip=f"Cabezal {p['nombre']}",
                icon=folium.Icon(color=color_well, icon='oil-well', prefix='fa')
            ).add_to(m)
            
        st.success(f"Logística trazada hacia {len(puntos_ruta)} cabezales de pozo.")

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error en la visualización: {e}")
