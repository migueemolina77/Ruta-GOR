import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests

st.set_page_config(page_title="Logística Rubiales - Kilometraje", layout="wide")

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

# 2. Función para obtener geometría y DISTANCIA de cada tramo
def obtener_tramo_real(punto_a, punto_b):
    url = f"http://router.project-osrm.org/route/v1/driving/{punto_a['lon']},{punto_a['lat']};{punto_b['lon']},{punto_b['lat']}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            ruta = data['routes'][0]
            geometria = [[coord[1], coord[0]] for coord in ruta['geometry']['coordinates']]
            distancia_km = ruta['distance'] / 1000  # Convertir metros a km
            return geometria, distancia_km
    except:
        pass
    return [], 0

@st.cache_data
def cargar_base_coordenadas(file_path):
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('Clúster').agg({
        'lat_dec': 'first', 'lon_dec': 'first', 'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("🚜 Planificador de Rutas con Cálculo de KM")

# Colores para los trayectos
colores_tramos = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FFB833', '#33FFF5']

try:
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    st.sidebar.header("Itinerario de Movilización")
    ruta_input = st.sidebar.text_area("Lista de Clústeres:", placeholder="RB-162\nRB-169\nRB-119")
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for nombre in nombres_ruta:
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({'nombre': nombre, 'lat': match.iloc[0]['lat_dec'], 'lon': match.iloc[0]['lon_dec'], 'pozos': match.iloc[0]['POZO']})

    m = folium.Map(location=[df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()], zoom_start=12, tiles="OpenStreetMap")

    distancia_total = 0
    resumen_ruta = []

    if len(puntos_ruta) >= 2:
        # Dibujar tramo por tramo
        for i in range(len(puntos_ruta) - 1):
            p1 = puntos_ruta[i]
            p2 = puntos_ruta[i+1]
            geometria, km = obtener_tramo_real(p1, p2)
            
            if geometria:
                color = colores_tramos[i % len(colores_tramos)]
                folium.PolyLine(geometria, color=color, weight=6, opacity=0.8, 
                                tooltip=f"Tramo {i+1}: {km:.2f} km").add_to(m)
                
                distancia_total += km
                resumen_ruta.append({"Tramo": f"{p1['nombre']} ➡️ {p2['nombre']}", "Distancia (Km)": round(km, 2)})
            else:
                # Línea recta de respaldo si no hay vía
                folium.PolyLine([[p1['lat'], p1['lon']], [p2['lat'], p2['lon']]], color='gray', dash_array='5').add_to(m)

        # Mostrar Resumen en la Sidebar
        st.sidebar.subheader("Resumen de Distancias")
        st.sidebar.table(resumen_ruta)
        st.sidebar.metric("Distancia Total", f"{distancia_total:.2f} Km")

    # Marcadores de Clúster
    for i, p in enumerate(puntos_ruta):
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=f"<b>{p['nombre']}</b>",
            icon=folium.Icon(color='black', icon='oil-well', prefix='fa')
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
