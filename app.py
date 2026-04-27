import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests
from folium.features import DivIcon

st.set_page_config(page_title="Logística GOR - Orden de Movilización", layout="wide")

# 1. Función para obtener tramos reales (OSRM)
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
    # CAMBIO 1: header=0 porque ahora los títulos están en la primera fila
    df = pd.read_excel(file_path, header=0)
    
    # Limpieza de nombres de columnas
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    # CAMBIO 2: Usar los nombres exactos del nuevo Excel (LATITUD / LONGITUD)
    # Como ya son decimales, solo nos aseguramos de que sean números
    df['lat_dec'] = pd.to_numeric(df['LATITUD'], errors='coerce')
    df['lon_dec'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
    
    # Agrupamos por CLUSTER (en mayúsculas como tu Excel)
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('CLUSTER').agg({
        'lat_dec': 'first', 
        'lon_dec': 'first', 
        'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()

st.title("🚜 Plan de Movilización Numerado - GOR")

colores_tramos = ['#E74C3C', '#2ECC71', '#3498DB', '#F1C40F', '#9B59B6', '#E67E22']

try:
    # Carga del nuevo archivo
    df_maestro = cargar_base_coordenadas("COORDENADAS GOR.xlsx")

    st.sidebar.header("Orden de Movilización")
    st.sidebar.write("Ejemplo: CLUSTER FAUNO, MITO 1")
    ruta_input = st.sidebar.text_area("Pega los Clústeres en orden:", placeholder="CLUSTER FAUNO\nMITO 1\nESTRACASU 4")
    
    # Normalizamos la entrada del usuario a mayúsculas
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for i, nombre in enumerate(nombres_ruta):
        match = df_maestro[df_maestro['CLUSTER'].astype(str).str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({
                'orden': i + 1,
                'nombre': nombre, 
                'lat': match.iloc[0]['lat_dec'], 
                'lon': match.iloc[0]['lon_dec'], 
                'pozos': match.iloc[0]['POZO']
            })

    # Centro del mapa basado en los datos cargados
    lat_inicial = df_maestro['lat_dec'].mean() if not df_maestro.empty else 3.7
    lon_inicial = df_maestro['lon_dec'].mean() if not df_maestro.empty else -71.7
    
    m = folium.Map(location=[lat_inicial, lon_inicial], zoom_start=11)

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

    # Marcadores
    for p in puntos_ruta:
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=f"<b>({p['orden']}) CLUSTER: {p['nombre']}</b><br>Pozos: {p['pozos']}",
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
    st.error(f"Error detectado: {e}")
    st.info("Asegúrate de que el archivo 'COORDENADAS GOR.xlsx' esté en GitHub y tenga las columnas: CLUSTER, POZO, LATITUD, LONGITUD.")
