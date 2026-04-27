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
            if pd.notna(lat) and pd.notna(lon):
                puntos_ruta.append({
                    'nombre': nombre,
                    'lat': lat,
                    'lon': lon,
                    'pozos': match.iloc[0]['POZO']
                })
        else:
            if nombre: st.sidebar.warning(f"⚠️ Clúster '{nombre}' no encontrado.")

    # 3. CONSTRUCCIÓN DEL MAPA
    # Centramos en el promedio de la base completa
    centro = [df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()]
    m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB positron")

    # Dibujar todos los clústeres disponibles como puntos de referencia
    for _, row in df_maestro.iterrows():
        folium.CircleMarker(
            location=[row['lat_dec'], row['lon_dec']],
            radius=2,
            color="#AAB7B8",
            fill=True,
            opacity=0.5
        ).add_to(m)

    # Dibujar la ruta si hay puntos válidos
    if puntos_ruta:
        coords_linea = [[p['lat'], p['lon']] for p in puntos_ruta]
        
        # Línea de trayectoria
        folium.PolyLine(
            coords_linea, 
            color="#28B463", 
            weight=4, 
            opacity=0.8
        ).add_to(m)

        # Marcadores de la ruta
        for i, p in enumerate(puntos_ruta):
            # Color: Verde para inicio, Rojo para fin, Azul para intermedios
            color_icon = 'green' if i == 0 else ('red' if i == len(puntos_ruta)-1 else 'blue')
            prefix = "INICIO" if i == 0 else ("DESTINO" if i == len(puntos_ruta)-1 else f"Punto {i}")
            
            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=folium.Popup(f"<b>{prefix}: {p['nombre']}</b><br>Pozos: {p['pozos']}", max_width=250),
                tooltip=f"{prefix}: {p['nombre']}",
                icon=folium.Icon(color=color_icon, icon='info-sign')
            ).add_to(m)

        st.success(f"Ruta trazada: {len(puntos_ruta)} puntos identificados.")
    else:
        st.info("Ingresa nombres de clústeres en la barra lateral para generar la ruta.")

    # Mostrar el mapa final
    st_folium(m, width=1100, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
    st.info("Revisa que el archivo 'Coordenadas Rubiales.xlsx' esté en la raíz de GitHub.")
