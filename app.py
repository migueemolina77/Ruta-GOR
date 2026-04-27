import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import requests
from folium.features import DivIcon

st.set_page_config(page_title="Logística GOR - Orden de Movilización", layout="wide")

# 1. Diccionario de Normalización (Campo -> Excel)
MAPEO_CAMPOS = {
    'RB': 'RUBIALES',
    'CASE': 'CAÑO SUR ESTE',
    'CSE': 'CAÑO SUR ESTE'
}

def normalizar_nombre(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    # Separa el prefijo del número/nombre (ej: CASE-027 -> CASE, 027)
    match = re.match(r"([A-Z]+)[-\s]*([A-Z0-9\s\-]+)", texto)
    if match:
        prefijo, resto = match.group(1), match.group(2)
        prefijo_real = MAPEO_CAMPOS.get(prefijo, prefijo)
        return f"{prefijo_real} {resto}".strip()
    return texto

# 2. Función para obtener rutas reales (OSRM)
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
    # Leemos el archivo (Header en fila 0 para COORDENADAS GOR.xlsx)
    df = pd.read_excel(file_path)
    df.columns = df.columns.astype(str).str.strip()
    
    # Normalizamos la columna CLUSTER del Excel para facilitar la búsqueda
    df['CLUSTER_NORM'] = df['CLUSTER'].apply(normalizar_nombre)
    
    # Convertimos coordenadas a números (asumiendo formato decimal del último archivo)
    df['lat_dec'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['lon_dec'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    # Agrupamos por CLUSTER para evitar puntos duplicados en el mapa
    return df.dropna(subset=['lat_dec', 'lon_dec']).groupby('CLUSTER_NORM').agg({
        'lat_dec': 'first', 
        'lon_dec': 'first', 
        'POZO': lambda x: ', '.join(x.astype(str).unique()),
        'CLUSTER': 'first' 
    }).reset_index()

st.title("🚜 Plan de Movilización Numerado - GOR")

colores_tramos = ['#E74C3C', '#2ECC71', '#3498DB', '#F1C40F', '#9B59B6', '#E67E22']

try:
    # IMPORTANTE: El nombre aquí debe ser EXACTO al de GitHub (minúsculas)
    # Si tu archivo se llama 'coordenadas.xlsx', cámbialo abajo:
    df_maestro = cargar_base_coordenadas("coordenadas.xlsx")

    st.sidebar.header("Orden de Movilización")
    st.sidebar.info("Puedes usar: CASE-027, RB-162, MITO 1")
    
    ruta_input = st.sidebar.text_area("Pega los Clústeres en orden:")
    nombres_solicitados = [normalizar_nombre(n) for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    puntos_ruta = []
    for i, nombre_buscado in enumerate(nombres_solicitados):
        # Búsqueda flexible (si el nombre está contenido en el registro)
        match = df_maestro[df_maestro['CLUSTER_NORM'].str.contains(nombre_buscado, na=False)]
        
        if not match.empty:
            puntos_ruta.append({
                'orden': i + 1,
                'nombre': match.iloc[0]['CLUSTER'], 
                'lat': match.iloc[0]['lat_dec'], 
                'lon': match.iloc[0]['lon_dec'], 
                'pozos': match.iloc[0]['POZO']
            })
        else:
            if nombre_buscado:
                st.sidebar.warning(f"⚠️ No encontrado: {nombre_buscado}")

    # Centro del mapa en GOR / Rubiales
    m = folium.Map(location=[3.74, -71.75], zoom_start=11, tiles="cartodbpositron")

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

    # Dibujar Marcadores Numerados
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
                html=f'''<div style="font-size: 14pt; color: white; background-color: black; 
                        border-radius: 50%; width: 30px; height: 30px; display: flex; 
                        justify-content: center; align-items: center; border: 2px solid white; 
                        font-weight: bold;">{p["orden"]}</div>''',
            )
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Asegúrate de que el archivo de Excel esté en la raíz de tu GitHub y el nombre coincida exactamente.")
