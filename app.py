import streamlit as st
import pandas as pd
import re

# 1. Configuración de la página
st.set_page_config(page_title="QAQC Registros de Producción - Rubiales", layout="wide")

# 2. Diccionario de Mapeo (Normalización de nombres de campo a OpenWells)
MAPEO_POZOS = {
    'RB': 'RUBIALES',
    'CASE': 'CAÑO SUR ESTE',
    'CSE': 'CAÑO SUR ESTE'
}

# 3. Función para normalizar la entrada del usuario
def normalizar_nombre_pozo(entrada_usuario):
    if not entrada_usuario:
        return ""
    
    # Convertir a mayúsculas y quitar espacios/puntos extra
    nombre = entrada_usuario.upper().strip().replace(".", "")
    
    # Expresión regular para separar prefijo de número (ej: RB-1065H o RB1065H)
    match = re.match(r"([A-Z]+)[-\s]*(\d+[A-Z]*)", nombre)
    
    if match:
        prefijo = match.group(1)
        numero = match.group(2)
        
        # Traducir prefijo (ej: RB -> RUBIALES)
        prefijo_oficial = MAPEO_POZOS.get(prefijo, prefijo)
        return f"{prefijo_oficial} {numero}"
    
    return nombre

# 4. Carga y limpieza de base de datos
@st.cache_data
def cargar_datos(archivo):
    # skipinitialspace elimina espacios después de las comas en el CSV
    df = pd.read_csv(archivo, skipinitialspace=True)
    
    # Limpiar espacios en blanco en las columnas críticas
    for col in ['POZO', 'CLUSTER', 'GERENCIA']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    return df

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Visualizador de RAW DATA - QAQC")
st.subheader("Coordinación de Subsuelo - Rubiales")

# Sidebar para cargar el archivo de coordenadas/OpenWells
with st.sidebar:
    st.header("Configuración")
    archivo_subido = st.file_uploader("Cargar base de datos (CSV)", type=["csv"])

if archivo_subido:
    df_base = cargar_datos(archivo_subido)
    
    # Buscador dinámico
    st.info("Puedes buscar como en campo (ej: RB-1065H) o como en OpenWells (RUBIALES 1065H)")
    busqueda = st.text_input("Ingrese el nombre del pozo a consultar:")
    
    if busqueda:
        nombre_normalizado = normalizar_nombre_pozo(busqueda)
        st.write(f"🔍 Buscando oficialmente como: **{nombre_normalizado}**")
        
        # Filtrado en el DataFrame
        resultado = df_base[df_base['POZO'] == nombre_normalizado]
        
        if not resultado.empty:
            # Mostrar métricas rápidas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pozo", resultado['POZO'].values[0])
            with col2:
                st.metric("Cluster", resultado['CLUSTER'].values[0])
            with col3:
                st.metric("Ubicación", f"{resultado['Latitud'].values[0]}, {resultado['Longitud'].values[0]}")
            
            # Espacio para el gráfico de registros (Raw Data)
            st.divider()
            st.subheader("Visualización de Registros")
            st.warning("Aquí se integrará la lógica de graficación de archivos .DLIS / Raw Data")
            
            # Mostrar tabla de datos completa del pozo
            st.dataframe(resultado)
        else:
            st.error(f"No se encontró el pozo '{nombre_normalizado}' en la base de datos.")
            st.info("Verifica que el nombre en el Excel coincida con el formato oficial.")

else:
    st.write("👈 Por favor, carga el archivo CSV de coordenadas en la barra lateral para iniciar.")

# Pie de página técnico
st.sidebar.markdown("---")
st.sidebar.caption("Desarrollado para la Implementación de visualizadores de RAW DATA.")
