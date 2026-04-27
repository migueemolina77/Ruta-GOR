import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests
from folium.features import DivIcon

st.set_page_config(page_title="Logística Rubiales - Orden de Movilización", layout="wide")

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

# 2. Función para obtener tramos reales
def obtener_tramo_real(punto_a, punto_b):
    url = f"http://router.project-osrm.org/route/v1/driving/{punto_a['lon']},{punto_a['lat']};{punto_b['lon']},{punto_b['lat']}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            ruta = data['routes'][0]
            geometria = [[coord[1], coord[0]] for coord in ruta['geometry']['coordinates']]
            distancia_km = ruta['distance'] / 1000
            return geometria, distancia_km
    except:
        pass
    return [], 0

@st.cache_data
def cargar_base_coordenadas(file_path):
    # Se mantiene header=6 asumiendo que los títulos están en la fila 7
    df = pd.read_excel(file_path, header=0)
    # Limpieza de nombres de columnas para evitar errores de espacios
    df.columns = df.columns.astype(str).str.strip()
    
    df['lat_dec'] = df['LATITUD'].apply(dms_to_decimal)
    df['lon_dec'] = df['LONGITUD'].apply(dms_to_decimal)
    
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('CLUSTER').agg({
        'lat_dec': 'first', 'lon_dec': 'first', 'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("🚜 Plan de Movilización Numerado")

colores_tramos = ['#E74C3C', '#2ECC71', '#3498DB', '#F1C40F', '#9B59B6', '#E67E22']

try:
    # --- CAMBIO REALIZADO AQUÍ ABAJO ---
    df_maestro = cargar_base_coordenadas("COORDENADAS GOR.xlsx")

    st.sidebar.header("Orden de Movilización")
    ruta_input = st.sidebar.text_area("Pega los Clústeres en orden:", placeholder="RB-162\nRB-269\nRB-119")
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for i, nombre in enumerate(nombres_ruta):
        match = df_maestro[df_maestro['Clúster'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({
                'orden': i + 1,
                'nombre': nombre, 
                'lat': match.iloc[0]['lat_dec'], 
                'lon': match.iloc[0]['lon_dec'], 
                'pozos': match.iloc[0]['POZO']
            })

    # Centro del mapa
    m = folium.Map(location=[df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()], zoom_start=12)

    if len(puntos_ruta) >= 2:
        resumen_ruta = []
        total_km = 0
        
        for i in range(len(puntos_ruta) - 1):
            p1, p2 = puntos_ruta[i], puntos_ruta[i+1]
            geometria, km = obtener_tramo_real(p1, p2)
            
            if geometria:
                color_asignado = colores_tramos[i % len(colores_tramos)]
                folium.PolyLine(geometria, color=color_asignado, weight=7, opacity=0.8).add_to(m)
                
                total_km += km
                resumen_ruta.append({
                    "Orden": f"{p1['orden']} ➡️ {p2['orden']}",
                    "Trayecto": f"{p1['nombre']} a {p2['nombre']}",
                    "KM": round(km, 2)
                })

        st.sidebar.subheader("Itinerario Detallado")
        st.sidebar.table(resumen_ruta)
        st.sidebar.metric("Distancia Total de Campaña", f"{total_km:.2f} Km")

    for p in puntos_ruta:
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=f"<b>({p['orden']}) Clúster: {p['nombre']}</b><br>Pozos: {p['pozos']}",
            icon=folium.Icon(color='black', icon='oil-well', prefix='fa')
        ).add_to(m)

        folium.map.Marker(
            [p['lat'], p['lon']],
            icon=DivIcon(
                icon_size=(150,36),
                icon_anchor=(7,20),
                html=f'<div style="font-size: 14pt; color: white; background-color: black; border-radius: 50%; width: 30px; height: 30px; display: flex; justify-content: center; align-items: center; border: 2px solid white; font-weight: bold;">{p["orden"]}</div>',
            )
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
