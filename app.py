import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests
from folium.features import DivIcon

st.set_page_config(page_title="Logística GOR - Orden de Movilización", layout="wide")

# 1. Diccionario de Normalización (Campo -> Búsqueda)
MAPEO_CAMPOS = {
    'RB': 'RUBIALES',
    'CASE': 'CAÑO SUR ESTE',
    'CSE': 'CAÑO SUR ESTE'
}

def normalizar_nombre(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    match = re.match(r"([A-Z]+)[-\s]*([A-Z0-9\s\-]+)", texto)
    if match:
        prefijo, resto = match.group(1), match.group(2)
        prefijo_real = MAPEO_CAMPOS.get(prefijo, prefijo)
        return f"{prefijo_real} {resto}".strip()
    return texto

# 2. Función para rutas reales (OSRM)
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
    # Intentamos cargar sin saltar filas primero (ajuste dinámico de header)
    df = pd.read_excel(file_path)
    
    # LIMPIEZA MAESTRA DE COLUMNAS:
    # Quitamos espacios, tildes y ponemos todo en MAYÚSCULAS
    df.columns = df.columns.astype(str).str.strip().str.upper().str.replace('Ú', 'U').str.replace('Ó', 'O')
    
    # Verificación de columnas mínimas necesarias
    columnas_requeridas = ['CLUSTER', 'LATITUD', 'LONGITUD', 'POZO']
    for col in columnas_requeridas:
        if col not in df.columns:
            st.error(f"⚠️ No se encontró la columna '{col}'. Las columnas detectadas son: {list(df.columns)}")
            st.stop()

    # Normalizamos la columna CLUSTER del Excel
    df['CLUSTER_NORM'] = df['CLUSTER'].apply(normalizar_nombre)
    
    # Convertimos coordenadas a números (manejo de errores para celdas vacías)
    df['LAT_DEC'] = pd.to_numeric(df['LATITUD'], errors='coerce')
    df['LON_DEC'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
    
    return df.dropna(subset=['LAT_DEC', 'LON_DEC']).groupby('CLUSTER_NORM').agg({
        'LAT_DEC': 'first', 
        'LON_DEC': 'first', 
        'POZO': lambda x: ', '.join(x.astype(str).unique()),
        'CLUSTER': 'first' 
    }).reset_index()

st.title("🚜 Plan de Movilización Numerado - GOR")

try:
    # Asegúrate de que el nombre sea el que tienes en GitHub
    df_maestro = cargar_base_coordenadas("coordenadas.xlsx")

    st.sidebar.header("Orden de Movilización")
    ruta_input = st.sidebar.text_area("Pega los Clústeres en orden:", placeholder="RB-162\nCASE-027")
    nombres_solicitados = [normalizar_nombre(n) for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for i, nombre_buscado in enumerate(nombres_solicitados):
        # Búsqueda flexible
        match = df_maestro[df_maestro['CLUSTER_NORM'].str.contains(nombre_buscado, na=False)]
        
        if not match.empty:
            puntos_ruta.append({
                'orden': i + 1,
                'nombre': match.iloc[0]['CLUSTER'], 
                'lat': match.iloc[0]['LAT_DEC'], 
                'lon': match.iloc[0]['LON_DEC'], 
                'pozos': match.iloc[0]['POZO']
            })
        else:
            if nombre_buscado:
                st.sidebar.warning(f"⚠️ No encontrado: {nombre_buscado}")

    # Mapa base
    m = folium.Map(location=[3.74, -71.75], zoom_start=11, tiles="cartodbpositron")

    if len(puntos_ruta) >= 2:
        total_km = 0
        for i in range(len(puntos_ruta) - 1):
            p1, p2 = puntos_ruta[i], puntos_ruta[i+1]
            geometria, km = obtener_tramo_real(p1, p2)
            if geometria:
                folium.PolyLine(geometria, color='#2E86C1', weight=6, opacity=0.8).add_to(m)
                total_km += km

        st.sidebar.metric("Distancia Total Estimada", f"{total_km:.2f} Km")

    # Marcadores
    for p in puntos_ruta:
        folium.Marker(
            location=[p['lat'], p['lon']],
            icon=DivIcon(
                icon_size=(35,35),
                icon_anchor=(17,17),
                html=f'<div style="font-size: 13pt; color: white; background-color: #1B2631; border-radius: 50%; width: 35px; height: 35px; display: flex; justify-content: center; align-items: center; border: 2px solid white; font-weight: bold;">{p["orden"]}</div>',
            ),
            popup=f"<b>Clúster:</b> {p['nombre']}<br><b>Pozos:</b> {p['pozos']}"
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
