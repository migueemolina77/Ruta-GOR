import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests
from folium.features import DivIcon

st.set_page_config(page_title="Logística GOR - Movilización", layout="wide")

# 1. Diccionario de Normalización (Campo -> Excel)
MAPEO_CAMPOS = {
    'RB': 'RUBIALES',
    'CASE': 'CAÑO SUR ESTE',
    'CSE': 'CAÑO SUR ESTE'
}

def normalizar_nombre(texto):
    if not texto or pd.isna(texto): return ""
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
    except: pass
    return [], 0

@st.cache_data
def cargar_base_coordenadas(file_path):
    # Cargamos el archivo sin saltar filas
    df = pd.read_excel(file_path)
    
    # --- LIMPIEZA DINÁMICA DE COLUMNAS ---
    # Convertimos todos los encabezados a string, mayúsculas y sin espacios
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Buscamos las columnas por palabras clave (así no importa si tienen espacios o tildes)
    def encontrar_columna(keywords):
        for kw in keywords:
            for col in df.columns:
                if kw in col: return col
        return None

    col_cluster = encontrar_columna(['CLUSTER', 'CLUS'])
    col_lat = encontrar_columna(['LATITUDE', 'LATITUD', 'LAT'])
    col_lon = encontrar_columna(['LONGITUDE', 'LONGITUD', 'LON'])
    col_pozo = encontrar_columna(['POZO', 'WELL'])

    if not all([col_cluster, col_lat, col_lon]):
        st.error(f"⚠️ No se encontraron las columnas necesarias. Detectadas: {list(df.columns)}")
        st.stop()

    # Limpieza de datos
    df['CLUSTER_NORM'] = df[col_cluster].apply(normalizar_nombre)
    df['LAT_NUM'] = pd.to_numeric(df[col_lat], errors='coerce')
    df['LON_NUM'] = pd.to_numeric(df[col_lon], errors='coerce')
    
    return df.dropna(subset=['LAT_NUM', 'LON_NUM']).groupby('CLUSTER_NORM').agg({
        'LAT_NUM': 'first', 
        'LON_NUM': 'first', 
        'POZO': lambda x: ', '.join(x.astype(str).unique()) if col_pozo else 'N/A',
        col_cluster: 'first' 
    }).reset_index().rename(columns={col_cluster: 'NOMBRE_ORIGINAL'})

st.title("🚜 Plan de Movilización Numerado - GOR")

try:
    # EL NOMBRE DEBE COINCIDIR CON GITHUB (USA MINÚSCULAS)
    df_maestro = cargar_base_coordenadas("coordenadas.xlsx")

    st.sidebar.header("Orden de Movilización")
    ruta_input = st.sidebar.text_area("Pega los Clústeres en orden:", placeholder="RB-162\nCASE-X8")
    
    nombres_solicitados = [normalizar_nombre(n) for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for i, nombre_buscado in enumerate(nombres_solicitados):
        # Búsqueda por coincidencia parcial para ser más dinámicos
        match = df_maestro[df_maestro['CLUSTER_NORM'].str.contains(nombre_buscado, na=False)]
        
        if not match.empty:
            puntos_ruta.append({
                'orden': i + 1,
                'nombre': match.iloc[0]['NOMBRE_ORIGINAL'], 
                'lat': match.iloc[0]['LAT_NUM'], 
                'lon': match.iloc[0]['LON_NUM'], 
                'pozos': match.iloc[0]['POZO']
            })
        else:
            if nombre_buscado: st.sidebar.warning(f"⚠️ No encontrado: {nombre_buscado}")

    # Configuración del Mapa
    m = folium.Map(location=[3.74, -71.75], zoom_start=11, tiles="cartodbpositron")

    if len(puntos_ruta) >= 2:
        resumen_ruta = []
        total_km = 0
        for i in range(len(puntos_ruta) - 1):
            p1, p2 = puntos_ruta[i], puntos_ruta[i+1]
            geometria, km = obtener_tramo_real(p1, p2)
            if geometria:
                folium.PolyLine(geometria, color='#E74C3C', weight=7, opacity=0.8).add_to(m)
                total_km += km
                resumen_ruta.append({"Orden": f"{p1['orden']}➡️{p2['orden']}", "Trayecto": f"{p1['nombre']} a {p2['nombre']}", "KM": round(km, 2)})

        st.sidebar.table(resumen_ruta)
        st.sidebar.metric("Distancia Total de Campaña", f"{total_km:.2f} Km")

    # Marcadores
    for p in puntos_ruta:
        folium.Marker(
            location=[p['lat'], p['lon']],
            icon=DivIcon(
                icon_size=(40,40), icon_anchor=(20,20),
                html=f'<div style="font-size: 14pt; color: white; background-color: #2C3E50; border-radius: 50%; width: 35px; height: 35px; display: flex; justify-content: center; align-items: center; border: 2px solid white; font-weight: bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">{p["orden"]}</div>'
            ),
            popup=f"<b>({p['orden']}) Clúster: {p['nombre']}</b><br>Pozos: {p['pozos']}"
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error crítico: {e}")
