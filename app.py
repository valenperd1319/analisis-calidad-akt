import streamlit as st
import pandas as pd
import numpy as np
import json
import sqlite3
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Análisis de Calidad — AKT Motos",
    page_icon="🏍",
    layout="wide",
    initial_sidebar_state="expanded"
)

KB = {'Tallado': {'tipo': 'Pintura', 'desc': 'Marcas superficiales en la pintura por contacto físico', 'causas': ['Manipulación sin guantes post-horno', 'Apilamiento sin separadores', 'Superficies de trabajo con bordes filosos', 'Embalaje inadecuado'], 'soluciones': ['Usar guantes de algodón en toda la cadena post-horno', 'Implementar separadores de espuma entre piezas', 'Revisar puntos de contacto en línea de producción', 'Establecer zonas de almacenamiento con soportes acolchados'], 'std': 'T', 'urgencia': 2}, 'Grumo': {'tipo': 'Pintura', 'desc': 'Partículas o protuberancias en la superficie mayores a 0.3mm', 'causas': ['Filtros de cabina saturados', 'Pintura sin colar antes de aplicar', 'Boquilla desgastada', 'Presión de atomización incorrecta', 'Temperatura de cabina muy alta'], 'soluciones': ['Cambiar filtros cada 100 horas o 3-4 semanas', 'Colar pintura con malla 100-150 micras', 'Verificar presión 1.5-2 bar en HVLP', 'Reemplazar boquillas mensualmente', 'Mantener cabina 20-25°C'], 'std': 'C', 'urgencia': 4}, 'Rayado': {'tipo': 'Pintura', 'desc': 'Arañazos que pueden llegar al sustrato', 'causas': ['Manipulación sin guantes o con materiales abrasivos', 'Empaque sin protección', 'Roce durante ensamble'], 'soluciones': ['Protocolo obligatorio de guantes de algodón', 'Bolsas o fundas de tela por pieza', 'Revisar puntos de contacto en línea de ensamble'], 'std': 'D', 'urgencia': 5}, 'Adherencia': {'tipo': 'Pintura', 'desc': 'Falta de anclaje de la pintura al sustrato', 'causas': ['Superficie contaminada con grasa o aceite', 'Omisión del promotor de adhesión en ABS/PP', 'Humedad en la superficie', 'Alta humedad ambiental en Colombia'], 'soluciones': ['Lavar con desengrasante antes de cada pieza', 'Aplicar promotor en piezas de ABS y PP (5-10 min oreo)', 'Verificar sustrato completamente seco', 'Controlar humedad relativa 40-60% en cabina'], 'std': 'D', 'urgencia': 5, 'colombia_note': 'En Colombia la alta humedad especialmente en temporadas de lluvia es un factor crítico. Usar catalizadores adaptados al clima tropical.'}, 'Ojo de pez': {'tipo': 'Pintura', 'desc': 'Cráteres circulares por contaminación con silicona o aceite', 'causas': ['Aire comprimido contaminado con aceite', 'Trapos con residuos de silicona', 'Productos con silicona cerca de la cabina'], 'soluciones': ['Instalar separador de agua y aceite en la línea de aire', 'Prohibir productos con silicona en el área', 'Limpiar cabina con desengrasante semanalmente'], 'std': 'C', 'urgencia': 3}, 'Diferente tono': {'tipo': 'Pintura', 'desc': 'Variación de color respecto a la probeta aprobada', 'causas': ['Mezcla incorrecta o diferente lote de pigmento', 'Variaciones de temperatura en el horno', 'Tiempo de mezcla insuficiente'], 'soluciones': ['Verificar número de lote antes de producción', 'Calibrar temperatura del horno periódicamente', 'Agitar la pintura mínimo 5 minutos antes de aplicar'], 'std': 'D', 'urgencia': 4}, 'Micro hervido': {'tipo': 'Pintura', 'desc': 'Pequeñas burbujas por disolventes atrapados', 'causas': ['Temperatura muy alta que seca la superficie antes del interior', 'Diluyente demasiado lento', 'Capas muy gruesas', 'Alta temperatura + humedad en Colombia'], 'soluciones': ['Usar diluyentes apropiados a la temperatura del día', 'Respetar tiempos de flash-off entre capas', 'Aplicar capas más delgadas', 'Controlar temperatura de cabina 20-25°C'], 'std': 'C', 'urgencia': 3, 'colombia_note': 'En ciudades de clima cálido ajustar el catalizador según recomendación del fabricante.'}, 'Pintura chorreada': {'tipo': 'Pintura', 'desc': 'Escurrimientos en superficies inclinadas', 'causas': ['Exceso de pintura en una pasada', 'Diluyente demasiado lento', 'Distancia de pistola muy corta'], 'soluciones': ['Aplicar capas más delgadas', 'Calibrar presión caudal y abanico', 'Mantener distancia constante 20-30 cm'], 'std': 'D', 'urgencia': 4}, 'Faltante de pintura': {'tipo': 'Pintura', 'desc': 'Zonas sin cobertura de pintura', 'causas': ['Boquilla tapada', 'Velocidad de aplicación alta', 'Presión insuficiente'], 'soluciones': ['Verificar boquilla antes de producción', 'Establecer revisión de todas las caras al salir del horno', 'Calibrar presión al inicio de cada turno'], 'std': 'D', 'urgencia': 5}, 'Hundido': {'tipo': 'Pintura', 'desc': 'Deformación o abolladura en la pieza', 'causas': ['Golpes durante manejo pre-pintado', 'Presión excesiva en herramentales', 'Impacto en transporte'], 'soluciones': ['Revisar piezas en recepción antes de ingresar al proceso', 'Usar soportes acolchados', 'Registrar piezas con defecto previo para trazabilidad'], 'std': 'D', 'urgencia': 5}, 'Piel naranja': {'tipo': 'Pintura', 'desc': 'Textura rugosa similar a piel de naranja', 'causas': ['Presión de atomización muy alta', 'Distancia de pistola muy grande', 'Diluyente muy rápido'], 'soluciones': ['Ajustar presión dentro del rango recomendado', 'Mantener distancia adecuada 20-30 cm', 'Usar diluyente apropiado a temperatura de trabajo'], 'std': 'C', 'urgencia': 2}, 'Oxidado': {'tipo': 'Pintura', 'desc': 'Corrosión del sustrato metálico', 'causas': ['Exposición a humedad sin protección', 'Falla en primer anticorrosivo', 'Almacenamiento inadecuado'], 'soluciones': ['Revisar proceso de imprimación y primer', 'Almacenar piezas metálicas en ambiente seco', 'Controlar tiempo entre preparación y pintado'], 'std': 'D', 'urgencia': 5}, 'Desprendimiento de pintura': {'tipo': 'Pintura', 'desc': 'La pintura se desprende en placas', 'causas': ['Falla grave de adherencia', 'Superficie contaminada con desmoldante', 'Curado incompleto'], 'soluciones': ['Verificar promotor en 100% de piezas plásticas', 'Revisar proceso de preparación de superficie', 'Confirmar temperatura y tiempo de curado'], 'std': 'D', 'urgencia': 5}, 'Defecto de pintura': {'tipo': 'Pintura', 'desc': 'Defecto genérico no clasificado', 'causas': ['Condiciones de cabina fuera de rango', 'Insumos con problemas de calidad'], 'soluciones': ['Clasificar el defecto para tomar acción correctiva', 'Revisar condiciones de cabina', 'Verificar calidad del lote en uso'], 'std': 'C', 'urgencia': 2}, 'Pintura contaminada': {'tipo': 'Pintura', 'desc': 'Pintura con partículas extrañas visibles', 'causas': ['Almacenamiento inadecuado', 'Recipientes sucios', 'Pintura vencida'], 'soluciones': ['Colar siempre la pintura antes de aplicar', 'Revisar condiciones de almacenamiento', 'Verificar fecha de vencimiento del lote'], 'std': 'C', 'urgencia': 3}, 'Pintura Levantada': {'tipo': 'Pintura', 'desc': 'La pintura se levanta en burbujas sin desprenderse', 'causas': ['Humedad atrapada debajo de la pintura', 'Temperatura de horno genera vapor', 'Capas muy gruesas'], 'soluciones': ['Sustrato completamente seco antes de pintar', 'Revisar temperatura de curado', 'Respetar tiempos de flash-off'], 'std': 'D', 'urgencia': 4}, 'Contaminado': {'tipo': 'Pintura', 'desc': 'Partículas externas incrustadas en la pintura', 'causas': ['Corrientes de aire con polvo en cabina', 'Personal sin indumentaria adecuada', 'Filtros saturados'], 'soluciones': ['Limpiar cabina al inicio de cada turno', 'Usar indumentaria antiestática', 'Verificar filtros semanalmente'], 'std': 'C', 'urgencia': 3}, 'Golpeado': {'tipo': 'Pintura', 'desc': 'Golpe visible en la pieza pintada', 'causas': ['Impacto durante manipulación post-pintura', 'Transporte sin protección', 'Caída durante proceso'], 'soluciones': ['Mejorar embalaje y protección en transporte', 'Revisar procedimientos de manipulación', 'Establecer almacenamiento temporal acolchado'], 'std': 'D', 'urgencia': 4}, 'Roto': {'tipo': 'Sillas', 'desc': 'Ruptura en estructura, tapizado o espuma del asiento', 'causas': ['Espuma de densidad insuficiente', 'Material de tapizado con baja resistencia', 'Grapas mal colocadas', 'Impacto durante manipulación'], 'soluciones': ['Verificar densidad de espuma mínimo 35 kg/m³', 'Revisar proceso de grapeado y tensado', 'Prueba de carga estática por lote', 'Mejorar embalaje para transporte'], 'std': 'D', 'urgencia': 5}, 'Falta buje': {'tipo': 'Sillas', 'desc': 'Ausencia del buje de sujeción del sillín', 'causas': ['Omisión en proceso de ensamble', 'Error en kit de piezas del proveedor'], 'soluciones': ['Verificación final de componentes antes del empaque', 'Implementar checklist visual por referencia'], 'std': 'D', 'urgencia': 5}, 'Base sillín no conforme': {'tipo': 'Sillas', 'desc': 'Base del sillín fuera de especificaciones', 'causas': ['Molde desgastado o fuera de calibración', 'Material de inyección diferente a especificación'], 'soluciones': ['Verificar dimensiones contra plano aprobado en recepción', 'Solicitar certificado de material por lote'], 'std': 'D', 'urgencia': 4}, 'Desgrapado de Silla': {'tipo': 'Sillas', 'desc': 'Tapizado se desprende por fallas en el grapeado', 'causas': ['Grapas de calibre insuficiente', 'Tensado incorrecto del tapizado', 'Proceso de grapeado sin control'], 'soluciones': ['Estandarizar calibre y tipo de grapa', 'Capacitar en técnica correcta de tensado', 'Prueba de jalado como control en proceso'], 'std': 'D', 'urgencia': 4}, 'Incompleto': {'tipo': 'Sillas', 'desc': 'Sillín con piezas faltantes', 'causas': ['Error en ensamble por omisión', 'Falta de control de piezas al final de línea'], 'soluciones': ['Checklist de componentes por referencia', 'Punto de control visual al final del proceso'], 'std': 'D', 'urgencia': 4}, 'Deforme': {'tipo': 'Sillas', 'desc': 'Forma del sillín diferente a especificación', 'causas': ['Espuma con densidad incorrecta', 'Almacenamiento incorrecto que genera deformación'], 'soluciones': ['Verificar forma contra muestra aprobada por lote', 'Revisar condiciones de almacenamiento'], 'std': 'C', 'urgencia': 3}, 'Ruido interno': {'tipo': 'Sillas', 'desc': 'Ruido o crujido al ejercer presión', 'causas': ['Componentes internos sueltos', 'Espuma que no cubre estructura interna'], 'soluciones': ['Prueba de presión manual en control de recepción', 'Verificar fijación de componentes internos'], 'std': 'C', 'urgencia': 3}, 'Falta platina': {'tipo': 'Sillas', 'desc': 'Ausencia de la platina metálica de sujeción', 'causas': ['Omisión en ensamble', 'Error en kit de componentes'], 'soluciones': ['Verificar componentes metálicos antes del empaque', 'Verificación por peso del conjunto'], 'std': 'D', 'urgencia': 5}, '_process_context': {'batch': {'nombre': 'Por lotes (horno cerrado)', 'riesgos': ['Variación de temperatura entre inicio y final del lote', 'Mayor manejo manual en carga y descarga']}, 'continuo': {'nombre': 'Línea continua (horno abierto)', 'riesgos': ['La puerta siempre abierta puede introducir partículas', 'Cambios de temperatura ambiental afectan el proceso']}}, '_process_recs': {'Grumo': {'batch': 'En proceso por lotes verificar que la temperatura esté estabilizada antes de cargar piezas y colar la pintura antes de cada lote.', 'continuo': 'En línea continua revisar si hay fuentes de polvo cerca de la entrada del túnel y aumentar frecuencia de revisión de filtros.'}, 'Micro hervido': {'batch': 'Revisar la uniformidad de temperatura dentro del horno y la rampa de calentamiento entre ciclos.', 'continuo': 'Verificar el tiempo de tránsito de las piezas por cada zona y que la velocidad de línea permita el aireado correcto.'}, 'Diferente tono': {'batch': 'Los primeros lotes del día pueden tener variación porque el horno no ha estabilizado temperatura. Esperar estabilización antes de producción de primera calidad.', 'continuo': 'Las variaciones aparecen al inicio y final de jornada. Establecer tiempo de estabilización de línea antes de producir.'}, 'Adherencia': {'batch': 'Asegurar que las piezas estén completamente secas antes de cargar el lote. El horno cerrado puede concentrar humedad residual.', 'continuo': 'En días lluviosos en Colombia la humedad que entra por la apertura del túnel puede afectar el curado. Ajustar catalizador en temporada de lluvias.'}, 'Ojo de pez': {'batch': 'Generalmente viene de contaminación en pistola o pintura. Revisar sistema de aire comprimido y limpieza de pistola antes de cada lote.', 'continuo': 'Puede venir de contaminación que entra por la apertura del túnel. Considerar cortina de aire en la entrada.'}, 'Tallado': {'batch': 'El mayor riesgo es en la carga y descarga manual del horno. Implementar protocolo específico con guantes y superficies acolchadas en esos momentos.', 'continuo': 'Revisar todos los puntos de contacto del transportador y protegerlos con materiales blandos.'}}, '_provider_process': {'SERVIPINTARTE': 'batch', 'INTERAUTOS': 'continuo'}}

WEIGHTS = {
    "Tallado":1,"Rayado":2,"Piel naranja":2,"Pintura tallada":2,
    "Diferente tono":2,"Diferente color":3,"Grumo":3,"Micro hervido":3,"Hundido":3,
    "Defecto de pintura":3,"Contaminado":3,"Pintura contaminada":3,"Textura defectuosa":3,
    "Ojo de pez":3,"Pintura chorreada":3,"Pintura Levantada":4,
    "Sin pintar":4,"Faltante de pintura":4,"Faltante":4,
    "Adherencia":5,"Desprendimiento de pintura":5,"Desprendimiento":5,
    "Oxidado":5,"Roto":5,"Reventado":5,"Golpeado":3,"Deforme":4,
    "Base sillín no conforme":4,"Desgrapado de Silla":4,"Incompleto":4,
    "Falta buje":5,"Falta platina":5,"Ruido interno":3,
}
STD = {
    "Adherencia":"D","Desprendimiento de pintura":"D","Desprendimiento":"D",
    "Pintura chorreada":"D","Rayado":"D","Faltante de pintura":"D","Sin pintar":"D",
    "Faltante":"D","Hundido":"D","Roto":"D","Reventado":"D","Diferente tono":"D",
    "Diferente color":"D","Pintura Levantada":"D","Oxidado":"D",
    "Falta buje":"D","Falta platina":"D","Incompleto":"D","Base sillín no conforme":"D",
    "Desgrapado de Silla":"D","Desprendimiento de pintura":"D",
    "Grumo":"C","Micro hervido":"C","Ojo de pez":"C","Piel naranja":"C",
    "Contaminado":"C","Pintura contaminada":"C","Textura defectuosa":"C",
    "Pintura tallada":"C","Defecto de pintura":"C","Deforme":"C","Ruido interno":"C",
    "Tallado":"T","Marca de lija":"T","Mal masillado":"T","Golpeado":"T",
}
PROV_PROCESS = {"SERVIPINTARTE":"batch","INTERAUTOS":"continuo"}
STD_COLORS = {"D":"#c0392b","C":"#c9840a","T":"#2d6b3f"}

MES_ORDER = ["enero","febrero","marzo","abril","mayo","junio",
    "julio","agosto","septiembre","octubre","noviembre","diciembre"]

def sort_mes(m):
    m_lower = str(m).lower()
    yr = next((s for s in str(m).split("-") if s.isdigit() and len(s)==4), "0000")
    mn = next((str(i).zfill(2) for i,n in enumerate(MES_ORDER) if n in m_lower), "99")
    return yr+mn

DB_PATH = "calidad_akt.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS periodos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, fecha_carga TEXT, registros INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo_id INTEGER, mes TEXT, proveedor TEXT,
        damage TEXT, tipo_averia TEXT, articulo TEXT,
        modelo TEXT, cantidad_pnc REAL, criticidad REAL, std TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS acciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo_id INTEGER, proveedor TEXT, defecto TEXT,
        accion TEXT, responsable TEXT, fecha_compromiso TEXT,
        estado TEXT, fecha_creacion TEXT, notas TEXT)""")
    con.commit(); con.close()

def safe_get(r, *keys):
    for k in keys:
        try:
            v = r[k]
            if v is not None and str(v) != "nan": return str(v)
        except: pass
    return ""

def save_periodo(nombre, df):
    # Normalize column names
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO periodos (nombre,fecha_carga,registros) VALUES (?,?,?)",
        (nombre, datetime.now().strftime("%Y-%m-%d %H:%M"), len(df)))
    pid = cur.lastrowid
    rows = []
    for _, r in df.iterrows():
        dmg = safe_get(r, "damage")
        pnc = float(r["cantidad_pnc"]) if "cantidad_pnc" in r.index and str(r["cantidad_pnc"]) not in ["","nan"] else 0.0
        modelo = safe_get(r, "Modelo", "modelo")
        rows.append((pid, safe_get(r,"mes"), safe_get(r,"nombre_proveedor"),
            dmg, safe_get(r,"tipo_averia"), safe_get(r,"articulo"),
            modelo, pnc, pnc*WEIGHTS.get(dmg,2), STD.get(dmg,"C")))
    cur.executemany("INSERT INTO registros (periodo_id,mes,proveedor,damage,tipo_averia,articulo,modelo,cantidad_pnc,criticidad,std) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()
    return pid

def get_periodos():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM periodos ORDER BY id DESC", con)
    con.close(); return df

def get_data(periodo_ids):
    if not periodo_ids: return pd.DataFrame()
    con = sqlite3.connect(DB_PATH)
    ids = ",".join(str(i) for i in periodo_ids)
    df = pd.read_sql(f"SELECT r.*, p.nombre as periodo_nombre FROM registros r JOIN periodos p ON r.periodo_id=p.id WHERE r.periodo_id IN ({ids})", con)
    con.close(); return df

def save_accion(pid, prov, defecto, accion, responsable, fecha, estado, notas):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO acciones (periodo_id,proveedor,defecto,accion,responsable,fecha_compromiso,estado,fecha_creacion,notas) VALUES (?,?,?,?,?,?,?,?,?)",
        (pid,prov,defecto,accion,responsable,fecha,estado,datetime.now().strftime("%Y-%m-%d"),notas))
    con.commit(); con.close()

def get_acciones(proveedor=None):
    con = sqlite3.connect(DB_PATH)
    q = "SELECT a.*, p.nombre as periodo_nombre FROM acciones a JOIN periodos p ON a.periodo_id=p.id"
    if proveedor: q += f" WHERE a.proveedor='{proveedor}'"
    df = pd.read_sql(q+" ORDER BY a.id DESC", con); con.close(); return df

def update_accion(accion_id, estado, notas=""):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE acciones SET estado=?,notas=? WHERE id=?",(estado,notas,accion_id))
    con.commit(); con.close()

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.main-title{font-family:'DM Serif Display',serif;font-size:1.9rem;color:#0f2718}
.kpi-card{background:#fff;border-radius:10px;padding:18px 20px;border:1px solid #f0ece2;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.kpi-val{font-family:'DM Serif Display',serif;font-size:1.8rem;color:#0f2718;line-height:1}
.kpi-lbl{font-size:.72rem;color:#8a9e8e;text-transform:uppercase;letter-spacing:.08em;margin-top:4px}
.sec-title{font-family:'DM Serif Display',serif;font-size:1.1rem;color:#0f2718;margin:1.2rem 0 .6rem}
.alert-reinc{background:#fdf0ef;border-left:4px solid #c0392b;padding:12px 16px;border-radius:0 8px 8px 0;margin:6px 0;font-size:.86rem}
.ac-pend{background:#fef9ed;border-left:3px solid #c9840a;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0}
.ac-done{background:#e8f5ec;border-left:3px solid #2d6b3f;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0}
.rec-D{background:#fdf0ef;border-left:3px solid #c0392b;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
.rec-C{background:#fef9ed;border-left:3px solid #c9840a;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
.rec-T{background:#e8f5ec;border-left:3px solid #2d6b3f;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
</style>""", unsafe_allow_html=True)

init_db()

# SIDEBAR
with st.sidebar:
    st.markdown("### 🏍 AKT Motos")
    st.markdown("**Análisis de Calidad**")
    st.divider()
    st.markdown("#### Cargar datos")
    uploaded = st.file_uploader("Master de averías (.xlsx)", type=["xlsx","xls"])
    if uploaded:
        nombre = st.text_input("Nombre del período", placeholder="Ej: Q1 2026")
        if st.button("💾 Guardar período", use_container_width=True):
            if not nombre:
                st.error("Escribe un nombre")
            else:
                with st.spinner("Procesando..."):
                    df_raw = pd.read_excel(uploaded, sheet_name="Datos")
                    # Normalize column names
                    df_raw.columns = [c.strip() for c in df_raw.columns]
                    if 'Modelo' in df_raw.columns: df_raw['modelo'] = df_raw['Modelo']
                    df_raw["cantidad_pnc"] = pd.to_numeric(df_raw.get("cantidad_pnc",0), errors="coerce").fillna(0)
                    save_periodo(nombre, df_raw)
                    st.success(f"✅ {nombre} guardado")
                    st.rerun()
    st.divider()
    periodos_df = get_periodos()
    if len(periodos_df)==0:
        st.info("Sube un master para comenzar")
        st.stop()
    periodo_options = {r["nombre"]:r["id"] for _,r in periodos_df.iterrows()}
    selected = st.multiselect("Períodos a analizar",
        list(periodo_options.keys()),
        default=[list(periodo_options.keys())[0]])
    if not selected:
        st.warning("Selecciona al menos un período")
        st.stop()
    selected_ids = [periodo_options[p] for p in selected]
    st.divider()
    with st.expander("⚙️ Gestión de datos"):
        if st.button("🗑️ Borrar todos los datos", use_container_width=True, type="secondary"):
            import os
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            st.success("Base de datos reiniciada")
            st.rerun()
        st.caption("Úsalo si necesitas volver a cargar los datos desde cero")
    st.divider()
    st.caption("Área de Desarrollo de Producto")
    st.caption("Valentina Perdomo Perdomo")

df = get_data(selected_ids)
if df.empty:
    st.warning("Sin datos"); st.stop()
df["cantidad_pnc"] = pd.to_numeric(df["cantidad_pnc"],errors="coerce").fillna(0)
df["criticidad"]   = pd.to_numeric(df["criticidad"],errors="coerce").fillna(0)
periodo_label = " + ".join(selected)

st.markdown(f'<div class="main-title">🏍 Análisis de Calidad — AKT Motos</div>', unsafe_allow_html=True)
st.markdown(f"**Período:** {periodo_label} · {len(df):,} registros · {df['proveedor'].nunique()} proveedores")
st.markdown("")

tabs = st.tabs(["📊 Resumen","🏭 Por proveedor","🔍 Por defecto","🔧 Por pieza","📈 Comparar períodos","📄 Exportar","🗂️ Períodos","✅ Acciones"])
tab_res, tab_prov, tab_def, tab_pie, tab_comp, tab_export, tab_mgmt, tab_acc = tabs

# ── TAB RESUMEN ──────────────────────────────────────────────
with tab_res:
    total = df["cantidad_pnc"].sum()
    pnc_D = df[df["std"]=="D"]["cantidad_pnc"].sum()
    pnc_C = df[df["std"]=="C"]["cantidad_pnc"].sum()
    pnc_T = df[df["std"]=="T"]["cantidad_pnc"].sum()
    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl in [
        (c1,f"{total:,.0f}","PNC Totales"),
        (c2,f"{pnc_D:,.0f}","Devolución directa"),
        (c3,f"{pnc_C:,.0f}","Condicional"),
        (c4,str(df["proveedor"].nunique()),"Proveedores")
    ]:
        col.markdown(f'<div class="kpi-card"><div class="kpi-val">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("")
    l, r = st.columns(2)
    with l:
        st.markdown('<div class="sec-title">PNC por proveedor</div>', unsafe_allow_html=True)
        pp = df.groupby("proveedor")["cantidad_pnc"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(pp,x="cantidad_pnc",y="proveedor",orientation="h",
            color="cantidad_pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
            labels={"cantidad_pnc":"PNC","proveedor":""},height=280)
        fig.update_layout(showlegend=False,margin=dict(l=0,r=0,t=5,b=0),
            plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
        st.plotly_chart(fig,use_container_width=True)
    with r:
        st.markdown('<div class="sec-title">Distribución STD-001</div>', unsafe_allow_html=True)
        sd = pd.DataFrame({"Tipo":["Devolución directa","Condicional","Tolerable"],"PNC":[pnc_D,pnc_C,pnc_T]})
        fig2 = px.pie(sd,values="PNC",names="Tipo",height=280,
            color="Tipo",color_discrete_map={"Devolución directa":"#c0392b","Condicional":"#c9840a","Tolerable":"#2d6b3f"})
        fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),paper_bgcolor="white")
        st.plotly_chart(fig2,use_container_width=True)

    st.markdown('<div class="sec-title">Tendencia mensual por proveedor</div>', unsafe_allow_html=True)
    mt = df.groupby(["mes","proveedor"])["cantidad_pnc"].sum().reset_index()
    if not mt.empty:
        mt["_sort"] = mt["mes"].apply(sort_mes)
        mt = mt.sort_values("_sort").drop(columns=["_sort"])
        fig3 = px.line(mt,x="mes",y="cantidad_pnc",color="proveedor",markers=True,
            labels={"cantidad_pnc":"PNC","mes":"Mes","proveedor":"Proveedor"},height=280,
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig3.update_layout(margin=dict(l=0,r=0,t=5,b=0),
            plot_bgcolor="white",paper_bgcolor="white",xaxis=dict(tickangle=-45))
        st.plotly_chart(fig3,use_container_width=True)

    if len(selected_ids)>1:
        st.markdown('<div class="sec-title">⚠️ Alertas de reincidencia entre períodos</div>', unsafe_allow_html=True)
        per = df.groupby(["periodo_nombre","proveedor","damage"])["cantidad_pnc"].sum().reset_index()
        reinc = per.groupby(["proveedor","damage"]).filter(lambda x: len(x)>=2)
        if not reinc.empty:
            for _, rw in reinc.groupby(["proveedor","damage"])["cantidad_pnc"].sum().sort_values(ascending=False).head(5).reset_index().iterrows():
                s = STD.get(rw["damage"],"C")
                icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
                st.markdown(f'<div class="alert-reinc">{icon} <strong>{rw["proveedor"]}</strong> — <strong>{rw["damage"]}</strong> aparece como crítico en {len(selected)} períodos consecutivos con {rw["cantidad_pnc"]:,.0f} PNC acumulados. Las acciones previas pueden no haber sido suficientes.</div>', unsafe_allow_html=True)
        else:
            st.success("✅ Sin defectos reincidentes entre los períodos seleccionados")

# ── TAB PROVEEDOR ────────────────────────────────────────────
with tab_prov:
    provs = sorted(df["proveedor"].unique())
    col1,col2,col3 = st.columns(3)
    prov_sel = col1.selectbox("Proveedor", provs)
    tipos = ["Todos"] + sorted(df["tipo_averia"].dropna().unique().tolist())
    tipo_sel = col2.selectbox("Tipo avería", tipos)
    std_sel = col3.selectbox("STD-001", ["Todos","D — Devolución","C — Condicional","T — Tolerable"])

    dfp = df[df["proveedor"]==prov_sel].copy()
    if tipo_sel!="Todos": dfp = dfp[dfp["tipo_averia"]==tipo_sel]
    if std_sel!="Todos": dfp = dfp[dfp["std"]==std_sel[0]]

    if dfp.empty:
        st.info("Sin datos para esta combinación")
    else:
        tot = dfp["cantidad_pnc"].sum()
        avg = dfp.groupby("mes")["cantidad_pnc"].sum().mean()
        pctD = dfp[dfp["std"]=="D"]["cantidad_pnc"].sum()/tot*100 if tot else 0
        proc = PROV_PROCESS.get(prov_sel)
        proc_lbl = "Por lotes" if proc=="batch" else "Línea continua" if proc=="continuo" else "—"

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("PNC Totales",f"{tot:,.0f}")
        k2.metric("Promedio mensual",f"{avg:,.0f}")
        k3.metric("% Devolución directa",f"{pctD:.0f}%")
        k4.metric("Tipo de proceso", proc_lbl)

        l2,r2 = st.columns(2)
        with l2:
            st.markdown('<div class="sec-title">Top defectos por criticidad</div>', unsafe_allow_html=True)
            td = dfp.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum"),crit=("criticidad","sum")).sort_values("crit",ascending=False).head(8).reset_index()
            fig = px.bar(td,x="pnc",y="damage",orientation="h",color="std",
                color_discrete_map=STD_COLORS,
                labels={"pnc":"PNC","damage":"","std":"STD"},height=300)
            fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)
        with r2:
            st.markdown('<div class="sec-title">Top piezas críticas</div>', unsafe_allow_html=True)
            tp = dfp.groupby("articulo").agg(pnc=("cantidad_pnc","sum")).sort_values("pnc",ascending=False).head(8).reset_index()
            fig2 = px.bar(tp,x="pnc",y="articulo",orientation="h",
                color="pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
                labels={"pnc":"PNC","articulo":""},height=300)
            fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
            st.plotly_chart(fig2,use_container_width=True)

        st.markdown('<div class="sec-title">Tendencia mensual</div>', unsafe_allow_html=True)
        md = dfp.groupby("mes")["cantidad_pnc"].sum().reset_index()
        md["_sort"] = md["mes"].apply(sort_mes)
        md = md.sort_values("_sort").drop(columns=["_sort"])
        avg_v = md["cantidad_pnc"].mean()
        md["Estado"] = md["cantidad_pnc"].apply(lambda v:"Anómalo (+30%)" if v>avg_v*1.3 else "Sobre promedio" if v>avg_v else "Normal")
        fig3 = px.bar(md,x="mes",y="cantidad_pnc",color="Estado",
            color_discrete_map={"Normal":"#52b06b","Sobre promedio":"#c9840a","Anómalo (+30%)":"#c0392b"},
            labels={"cantidad_pnc":"PNC","mes":""},height=260)
        fig3.add_hline(y=avg_v,line_dash="dot",line_color="#888",annotation_text=f"Prom: {avg_v:.0f}")
        fig3.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",xaxis=dict(tickangle=-45))
        st.plotly_chart(fig3,use_container_width=True)

        st.markdown('<div class="sec-title">💡 Recomendaciones según datos y proceso</div>', unsafe_allow_html=True)
        for _, rw in td.head(4).iterrows():
            kbE = KB.get(rw["damage"],{})
            s = rw["std"]
            causas = kbE.get("causas",[])
            sols = kbE.get("soluciones",[])
            proc_recs = KB.get("_process_recs",{}).get(rw["damage"],{})
            proc_rec = proc_recs.get(proc,"") if proc else ""
            col_note = kbE.get("colombia_note","")
            icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
            std_lbl = "Devolución directa" if s=="D" else "Condicional" if s=="C" else "Tolerable"
            txt = f"{rw['pnc']:,.0f} PNC · {std_lbl}. "
            if causas: txt += f"Causa frecuente: {causas[0]}. "
            if sols: txt += f"Se recomienda: {sols[0]}. "
            if proc_rec: txt += f"Para {proc_lbl.lower()}: {proc_rec} "
            if col_note: txt += f"Nota Colombia: {col_note}"
            st.markdown(f'<div class="rec-{s}">{icon} <strong>{rw["damage"]}</strong><br><span style="font-size:.83rem">{txt}</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-title">Tabla de trazabilidad</div>', unsafe_allow_html=True)
        tbl = dfp.groupby(["damage","std","articulo"]).agg(PNC=("cantidad_pnc","sum"),Crit=("criticidad","sum")).sort_values("Crit",ascending=False).reset_index()
        tbl["STD"] = tbl["std"].map({"D":"🔴 Dev.","C":"🟡 Cond.","T":"🟢 Tol."})
        tbl = tbl[["damage","STD","articulo","PNC","Crit"]].rename(columns={"damage":"Defecto","articulo":"Pieza","Crit":"Criticidad"})
        tbl["PNC"] = tbl["PNC"].apply(lambda x:f"{x:,.0f}")
        tbl["Criticidad"] = tbl["Criticidad"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(tbl,use_container_width=True,hide_index=True)

# ── TAB DEFECTO ──────────────────────────────────────────────
with tab_def:
    c1,c2 = st.columns(2)
    dmg_sel = c1.selectbox("Defecto",["Todos"]+sorted(df["damage"].dropna().unique().tolist()))
    std_f   = c2.selectbox("STD-001",["Todos","D — Devolución","C — Condicional","T — Tolerable"],key="std_d")

    dfd = df.copy()
    if dmg_sel!="Todos": dfd = dfd[dfd["damage"]==dmg_sel]
    if std_f!="Todos": dfd = dfd[dfd["std"]==std_f[0]]

    if not dfd.empty:
        if dmg_sel!="Todos":
            kbE = KB.get(dmg_sel,{})
            if kbE:
                s = STD.get(dmg_sel,"C")
                border = "#c0392b" if s=="D" else "#c9840a" if s=="C" else "#2d6b3f"
                bg = "#fdf0ef" if s=="D" else "#fef9ed" if s=="C" else "#e8f5ec"
                causas_txt = "; ".join(kbE.get("causas",[])[:3])
                st.markdown(f'<div style="background:{bg};border-left:4px solid {border};padding:12px 16px;border-radius:0 10px 10px 0;margin-bottom:12px"><strong>{dmg_sel}</strong> — {kbE.get("desc","")}<br><span style="font-size:.82rem;color:#555">Causas: {causas_txt}</span></div>', unsafe_allow_html=True)

        l3,r3 = st.columns(2)
        with l3:
            st.markdown('<div class="sec-title">Por proveedor</div>', unsafe_allow_html=True)
            bp = dfd.groupby("proveedor")["cantidad_pnc"].sum().sort_values(ascending=False).reset_index()
            fig = px.bar(bp,x="proveedor",y="cantidad_pnc",
                color="cantidad_pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
                labels={"cantidad_pnc":"PNC","proveedor":""},height=260)
            fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
        with r3:
            st.markdown('<div class="sec-title">Por modelo</div>', unsafe_allow_html=True)
            bm = dfd.groupby("modelo")["cantidad_pnc"].sum().sort_values(ascending=False).head(8).reset_index()
            fig2 = px.bar(bm,x="cantidad_pnc",y="modelo",orientation="h",
                color_discrete_sequence=["#3a8a51"],labels={"cantidad_pnc":"PNC","modelo":""},height=260)
            fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig2,use_container_width=True)

        st.markdown('<div class="sec-title">Trazabilidad por pieza y proveedor</div>', unsafe_allow_html=True)
        tbl2 = dfd.groupby(["proveedor","damage","articulo","std"]).agg(PNC=("cantidad_pnc","sum"),Crit=("criticidad","sum")).sort_values("Crit",ascending=False).reset_index()
        tbl2["STD"] = tbl2["std"].map({"D":"🔴 Dev.","C":"🟡 Cond.","T":"🟢 Tol."})
        tbl2 = tbl2[["proveedor","damage","articulo","STD","PNC","Crit"]].rename(columns={"proveedor":"Proveedor","damage":"Defecto","articulo":"Pieza","Crit":"Criticidad"})
        tbl2["PNC"] = tbl2["PNC"].apply(lambda x:f"{x:,.0f}")
        tbl2["Criticidad"] = tbl2["Criticidad"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(tbl2,use_container_width=True,hide_index=True)

# ── TAB PIEZA ────────────────────────────────────────────────
with tab_pie:
    c1,c2 = st.columns(2)
    prov_p = c1.selectbox("Proveedor",["Todos"]+sorted(df["proveedor"].unique().tolist()),key="prov_p")
    sort_p = c2.selectbox("Ordenar por",["Criticidad","PNC total","Devoluciones directas"])

    dfpi = df.copy()
    if prov_p!="Todos": dfpi = dfpi[dfpi["proveedor"]==prov_p]

    if not dfpi.empty:
        agg = dfpi.groupby(["articulo","proveedor"]).apply(lambda x: pd.Series({
            "PNC":x["cantidad_pnc"].sum(),
            "Criticidad":x["criticidad"].sum(),
            "Dev_D":x[x["std"]=="D"]["cantidad_pnc"].sum(),
            "Top_defecto": x.groupby("damage")["cantidad_pnc"].sum().idxmax() if len(x)>0 else ""
        })).reset_index()

        if sort_p=="Criticidad": agg = agg.sort_values("Criticidad",ascending=False)
        elif sort_p=="PNC total": agg = agg.sort_values("PNC",ascending=False)
        else: agg = agg.sort_values("Dev_D",ascending=False)
        agg = agg.head(15)

        fig = px.bar(agg,x="Criticidad",y="articulo",orientation="h",color="proveedor",
            labels={"Criticidad":"Índice Criticidad","articulo":""},height=480,
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

        show = agg.copy()
        show["PNC"] = show["PNC"].apply(lambda x:f"{x:,.0f}")
        show["Criticidad"] = show["Criticidad"].apply(lambda x:f"{x:,.0f}")
        show["Dev. Directas"] = show["Dev_D"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(show[["articulo","proveedor","PNC","Dev. Directas","Criticidad","Top_defecto"]].rename(columns={"articulo":"Pieza","proveedor":"Proveedor","Top_defecto":"Defecto principal"}),use_container_width=True,hide_index=True)

# ── TAB COMPARAR ─────────────────────────────────────────────
with tab_comp:
    all_periods = list(periodo_options.keys())
    if len(all_periods) < 2:
        st.info("Necesitas al menos 2 períodos guardados para comparar. Sube más archivos.")
    else:
        st.markdown('<div class="sec-title">Selecciona dos períodos para comparar</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        per_a = cc1.selectbox("Período A (base)", all_periods, index=0, key="comp_a")
        per_b = cc2.selectbox("Período B (comparar)", all_periods, index=min(1,len(all_periods)-1), key="comp_b")

        if per_a == per_b:
            st.warning("Selecciona dos períodos diferentes")
        else:
            id_a = periodo_options[per_a]
            id_b = periodo_options[per_b]
            df_a = get_data([id_a])
            df_b = get_data([id_b])

            if df_a.empty or df_b.empty:
                st.warning("Uno de los períodos no tiene datos")
            else:
                df_a["cantidad_pnc"] = pd.to_numeric(df_a["cantidad_pnc"],errors="coerce").fillna(0)
                df_b["cantidad_pnc"] = pd.to_numeric(df_b["cantidad_pnc"],errors="coerce").fillna(0)

                # KPI comparison
                st.markdown('<div class="sec-title">Resumen general</div>', unsafe_allow_html=True)
                tot_a = df_a["cantidad_pnc"].sum()
                tot_b = df_b["cantidad_pnc"].sum()
                dev_a = df_a[df_a["std"]=="D"]["cantidad_pnc"].sum()
                dev_b = df_b[df_b["std"]=="D"]["cantidad_pnc"].sum()
                pctD_a = dev_a/tot_a*100 if tot_a else 0
                pctD_b = dev_b/tot_b*100 if tot_b else 0

                k1,k2,k3,k4 = st.columns(4)
                delta_tot = tot_b - tot_a
                delta_dev = dev_b - dev_a
                k1.metric(f"PNC — {per_a}", f"{tot_a:,.0f}")
                k2.metric(f"PNC — {per_b}", f"{tot_b:,.0f}",
                    delta=f"{delta_tot:+,.0f} ({delta_tot/tot_a*100:+.1f}%)" if tot_a else None,
                    delta_color="inverse")
                k3.metric(f"Dev. Directa — {per_a}", f"{dev_a:,.0f} ({pctD_a:.0f}%)")
                k4.metric(f"Dev. Directa — {per_b}", f"{dev_b:,.0f} ({pctD_b:.0f}%)",
                    delta=f"{delta_dev:+,.0f}" if dev_a else None,
                    delta_color="inverse")

                # Comparativo por proveedor
                st.markdown('<div class="sec-title">Comparativo por proveedor</div>', unsafe_allow_html=True)
                prov_a = df_a.groupby("proveedor")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_a})
                prov_b = df_b.groupby("proveedor")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_b})
                prov_cmp = prov_a.merge(prov_b, on="proveedor", how="outer").fillna(0)
                prov_cmp["Δ PNC"] = prov_cmp[per_b] - prov_cmp[per_a]
                prov_cmp["Δ %"] = prov_cmp.apply(
                    lambda r: f"{r['Δ PNC']/r[per_a]*100:+.1f}%" if r[per_a]>0 else "N/A", axis=1)
                prov_cmp["Tendencia"] = prov_cmp["Δ PNC"].apply(
                    lambda x: "🔴 Empeoró" if x>0 else "🟢 Mejoró" if x<0 else "➡️ Igual")
                prov_cmp[per_a] = prov_cmp[per_a].apply(lambda x: f"{x:,.0f}")
                prov_cmp[per_b] = prov_cmp[per_b].apply(lambda x: f"{x:,.0f}")
                prov_cmp["Δ PNC"] = prov_cmp["Δ PNC"].apply(lambda x: f"{x:+,.0f}")
                st.dataframe(prov_cmp[["proveedor",per_a,per_b,"Δ PNC","Δ %","Tendencia"]]
                    .rename(columns={"proveedor":"Proveedor"}),
                    use_container_width=True, hide_index=True)

                # Gráfica comparativa
                prov_a2 = df_a.groupby("proveedor")["cantidad_pnc"].sum().reset_index()
                prov_a2["periodo"] = per_a
                prov_b2 = df_b.groupby("proveedor")["cantidad_pnc"].sum().reset_index()
                prov_b2["periodo"] = per_b
                prov_plot = pd.concat([prov_a2, prov_b2])
                fig = px.bar(prov_plot, x="proveedor", y="cantidad_pnc", color="periodo",
                    barmode="group", height=300,
                    labels={"cantidad_pnc":"PNC","proveedor":"","periodo":"Período"},
                    color_discrete_sequence=["#3a8a51","#2d65aa"])
                fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),
                    plot_bgcolor="white",paper_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

                # Top defectos comparativo
                st.markdown('<div class="sec-title">Top defectos — comparativo</div>', unsafe_allow_html=True)
                def_a = df_a.groupby("damage")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_a})
                def_b = df_b.groupby("damage")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_b})
                def_cmp = def_a.merge(def_b, on="damage", how="outer").fillna(0)
                def_cmp["Δ"] = def_cmp[per_b] - def_cmp[per_a]
                def_cmp = def_cmp.sort_values(per_b, ascending=False).head(10)
                def_cmp["STD"] = def_cmp["damage"].map(STD).map({"D":"🔴","C":"🟡","T":"🟢"}).fillna("⚪")
                def_cmp["Tendencia"] = def_cmp["Δ"].apply(lambda x: "⬆️" if x>0 else "⬇️" if x<0 else "➡️")
                def_cmp[per_a] = def_cmp[per_a].apply(lambda x: f"{x:,.0f}")
                def_cmp[per_b] = def_cmp[per_b].apply(lambda x: f"{x:,.0f}")
                def_cmp["Δ"] = def_cmp["Δ"].apply(lambda x: f"{x:+,.0f}")
                st.dataframe(def_cmp[["STD","damage",per_a,per_b,"Δ","Tendencia"]]
                    .rename(columns={"damage":"Defecto"}),
                    use_container_width=True, hide_index=True)

                # ── INTERPRETACIÓN AUTOMÁTICA ──
                st.markdown('<div class="sec-title">🔍 Qué cambió — interpretación automática</div>', unsafe_allow_html=True)

                def_a_raw = df_a.groupby("damage")["cantidad_pnc"].sum()
                def_b_raw = df_b.groupby("damage")["cantidad_pnc"].sum()
                pie_a_raw = df_a.groupby("articulo")["cantidad_pnc"].sum()
                pie_b_raw = df_b.groupby("articulo")["cantidad_pnc"].sum()
                prov_a_raw = df_a.groupby("proveedor")["cantidad_pnc"].sum()
                prov_b_raw = df_b.groupby("proveedor")["cantidad_pnc"].sum()

                insights = []
                delta_pct = (tot_b - tot_a) / tot_a * 100 if tot_a else 0

                # 1. Tendencia general
                if abs(delta_pct) >= 5:
                    dir_txt = f"aumentaron un **{abs(delta_pct):.0f}%**" if delta_pct > 0 else f"bajaron un **{abs(delta_pct):.0f}%**"
                    color = "#fdf0ef" if delta_pct > 0 else "#e8f5ec"
                    border = "#c0392b" if delta_pct > 0 else "#2d6b3f"
                    icon = "📈" if delta_pct > 0 else "📉"
                    nota = "Se recomienda revisar qué cambió en el proceso durante este período." if delta_pct > 0 else "Buena señal — las acciones tomadas pueden estar teniendo efecto."
                    insights.append((color, border, icon,
                        f"Los PNC totales {dir_txt} entre {per_a} y {per_b} ({tot_a:,.0f} → {tot_b:,.0f} PNC). {nota}"))

                # 2. Por proveedor
                for prov in prov_b_raw.index:
                    va = prov_a_raw.get(prov, 0)
                    vb = prov_b_raw.get(prov, 0)
                    if va > 0 and vb > 0:
                        dp = (vb - va) / va * 100
                        proc = PROV_PROCESS.get(prov, "")
                        proc_ctx = KB.get("_process_context", {}).get(proc, {})
                        proc_note = f" ({proc_ctx.get('nombre', '')})" if proc_ctx else ""
                        if dp > 20:
                            insights.append(("#fdf0ef", "#c0392b", "🔴",
                                f"**{prov}**{proc_note} empeoró: pasó de {va:,.0f} a {vb:,.0f} PNC (+{dp:.0f}%). "
                                "Puede indicar cambio de lote, aumento de producción sin ajuste de controles, o mantenimiento pendiente."))
                        elif dp < -20:
                            insights.append(("#e8f5ec", "#2d6b3f", "✅",
                                f"**{prov}**{proc_note} mejoró: bajó de {va:,.0f} a {vb:,.0f} PNC ({dp:.0f}%). "
                                "Las acciones tomadas en el período anterior pueden estar dando resultado."))

                # 3. Por defecto
                all_dmg = set(def_a_raw.index) | set(def_b_raw.index)
                for dmg in all_dmg:
                    va = def_a_raw.get(dmg, 0)
                    vb = def_b_raw.get(dmg, 0)
                    std = STD.get(dmg, "C")
                    if va > 50 or vb > 50:
                        dp = (vb - va) / va * 100 if va > 0 else 100
                        kbE = KB.get(dmg, {})
                        causa = kbE.get("causas", [""])[0] if kbE.get("causas") else ""
                        sol = kbE.get("soluciones", [""])[0] if kbE.get("soluciones") else ""
                        causa_txt = f" Causa frecuente: {causa}." if causa else ""
                        sol_txt = f" Se recomienda: {sol}." if sol else ""
                        if dp > 30 and std == "D":
                            insights.append(("#fdf0ef", "#c0392b", "🔴",
                                f"**{dmg}** (devolución directa) subió {dp:.0f}%: {va:,.0f} → {vb:,.0f} PNC.{causa_txt}{sol_txt}"))
                        elif dp > 40 and std == "C":
                            insights.append(("#fef9ed", "#c9840a", "🟡",
                                f"**{dmg}** (condicional) aumentó {dp:.0f}%: {va:,.0f} → {vb:,.0f} PNC.{causa_txt}"))
                        elif dp < -30 and vb > 20:
                            insights.append(("#e8f5ec", "#2d6b3f", "✅",
                                f"**{dmg}** bajó {abs(dp):.0f}%: {va:,.0f} → {vb:,.0f} PNC. "
                                "Posible efecto de acciones correctivas implementadas."))

                # 4. Por pieza
                all_pie = set(pie_a_raw.index) | set(pie_b_raw.index)
                pie_changes = []
                for pie in all_pie:
                    va = pie_a_raw.get(pie, 0)
                    vb = pie_b_raw.get(pie, 0)
                    if (va > 100 or vb > 100) and va > 0:
                        dp = (vb - va) / va * 100
                        if abs(dp) > 30:
                            pie_changes.append((pie, va, vb, dp))
                pie_changes.sort(key=lambda x: abs(x[3]), reverse=True)
                for pie, va, vb, dp in pie_changes[:3]:
                    if dp > 0:
                        insights.append(("#fdf0ef", "#c0392b", "📦",
                            f"**{pie}** subió {dp:.0f}% en PNC: {va:,.0f} → {vb:,.0f}. "
                            "Esta pieza merece revisión específica en el siguiente período."))
                    else:
                        insights.append(("#e8f5ec", "#2d6b3f", "📦",
                            f"**{pie}** bajó {abs(dp):.0f}% en PNC: {va:,.0f} → {vb:,.0f}. "
                            "Mejora significativa en esta pieza."))

                # 5. % Devolución directa
                if pctD_a > 0:
                    delta_d = pctD_b - pctD_a
                    if delta_d > 5:
                        insights.append(("#fdf0ef", "#c0392b", "⚠️",
                            f"El porcentaje de devolución directa subió de {pctD_a:.0f}% a {pctD_b:.0f}%. "
                            "Más defectos están en categorías que no se pueden tolerar — revisar proceso con urgencia."))
                    elif delta_d < -5:
                        insights.append(("#e8f5ec", "#2d6b3f", "✅",
                            f"El porcentaje de devolución directa bajó de {pctD_a:.0f}% a {pctD_b:.0f}%. "
                            "Los defectos críticos se están reduciendo — buena tendencia."))

                # Render
                if not insights:
                    st.success("✅ No se detectaron cambios significativos entre los dos períodos. La calidad se mantuvo estable.")
                else:
                    for bg, border, icon, txt in insights:
                        st.markdown(
                            f'<div style="background:{bg};border-left:4px solid {border};'
                            f'padding:12px 18px;border-radius:0 10px 10px 0;margin:6px 0;line-height:1.6">'
                            f'{icon} {txt}</div>',
                            unsafe_allow_html=True)


# ── TAB EXPORTAR ─────────────────────────────────────────────
with tab_export:
    st.markdown('<div class="sec-title">Exportar resumen ejecutivo por proveedor</div>', unsafe_allow_html=True)

    provs_exp = sorted(df["proveedor"].unique())
    col_e1, col_e2 = st.columns(2)
    prov_exp = col_e1.selectbox("Proveedor", provs_exp, key="exp_prov")
    df_exp = df[df["proveedor"]==prov_exp].copy()

    if not df_exp.empty:
        tot_e   = df_exp["cantidad_pnc"].sum()
        avg_e   = df_exp.groupby("mes")["cantidad_pnc"].sum().mean()
        pctD_e  = df_exp[df_exp["std"]=="D"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
        pctC_e  = df_exp[df_exp["std"]=="C"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
        pctT_e  = df_exp[df_exp["std"]=="T"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
        top5_def = df_exp.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum")).sort_values("pnc",ascending=False).head(5).reset_index()
        top5_pie = df_exp.groupby("articulo")["cantidad_pnc"].sum().sort_values(ascending=False).head(5).reset_index()
        mes_data = df_exp.groupby("mes")["cantidad_pnc"].sum().reset_index()
        mes_data["_sort"] = mes_data["mes"].apply(sort_mes)
        mes_data = mes_data.sort_values("_sort")
        proc_e   = PROV_PROCESS.get(prov_exp,"")
        proc_lbl_e = "Por lotes (horno cerrado)" if proc_e=="batch" else "Línea continua (horno abierto)" if proc_e=="continuo" else "No especificado"

        # Build bar chart as base64
        import plotly.io as pio, base64, io
        avg_v = mes_data["cantidad_pnc"].mean()
        mes_data["Estado"] = mes_data["cantidad_pnc"].apply(
            lambda v:"Anómalo" if v>avg_v*1.3 else "Sobre promedio" if v>avg_v else "Normal")
        fig_trend = px.bar(mes_data, x="mes", y="cantidad_pnc", color="Estado",
            color_discrete_map={"Normal":"#52b06b","Sobre promedio":"#c9840a","Anómalo":"#c0392b"},
            height=220, labels={"cantidad_pnc":"PNC","mes":""})
        fig_trend.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=10,b=40),
            plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#333"),
            showlegend=True, legend=dict(orientation="h",y=-0.3),
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)))
        trend_img = base64.b64encode(pio.to_image(fig_trend, format="png", width=700, height=220)).decode()

        fig_pie_chart = px.pie(
            values=[df_exp[df_exp["std"]=="D"]["cantidad_pnc"].sum(),
                    df_exp[df_exp["std"]=="C"]["cantidad_pnc"].sum(),
                    df_exp[df_exp["std"]=="T"]["cantidad_pnc"].sum()],
            names=["Devolución directa","Condicional","Tolerable"],
            color_discrete_map={"Devolución directa":"#c0392b","Condicional":"#c9840a","Tolerable":"#2d6b3f"},
            height=200)
        fig_pie_chart.update_layout(template="plotly_white", margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor="white", font=dict(color="#333"),
            legend=dict(font=dict(size=10)))
        pie_img = base64.b64encode(pio.to_image(fig_pie_chart, format="png", width=320, height=200)).decode()

        # Build defectos bars
        top5_def_sorted = top5_def.copy()
        fig_def = px.bar(top5_def_sorted, x="pnc", y="damage", orientation="h",
            color="std", color_discrete_map=STD_COLORS,
            height=200, labels={"pnc":"PNC","damage":"","std":"STD"})
        fig_def.update_layout(template="plotly_white", margin=dict(l=0,r=10,t=10,b=0),
            plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#333"),
            legend=dict(font=dict(size=10), orientation="h", y=-0.3))
        def_img = base64.b64encode(pio.to_image(fig_def, format="png", width=380, height=200)).decode()

        # STD rows
        std_rows = ""
        for _, r in top5_def.iterrows():
            s = r["std"]
            badge_color = "#c0392b" if s=="D" else "#c9840a" if s=="C" else "#2d6b3f"
            badge_bg = "#fdf0ef" if s=="D" else "#fef9ed" if s=="C" else "#e8f5ec"
            badge_lbl = "Devolución" if s=="D" else "Condicional" if s=="C" else "Tolerable"
            pct = r["pnc"]/tot_e*100 if tot_e else 0
            std_rows += f"""<tr>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2">{r['damage']}</td>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2;text-align:center">
                <span style="background:{badge_bg};color:{badge_color};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600">{badge_lbl}</span>
              </td>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r['pnc']:,.0f}</td>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2;text-align:right;color:#888">{pct:.1f}%</td>
            </tr>"""

        pie_rows = ""
        for i, r in top5_pie.iterrows():
            pie_rows += f"""<tr>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2;color:#3a8a51;font-weight:600">{i+1}</td>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2">{r['articulo']}</td>
              <td style="padding:7px 10px;font-size:12px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r['cantidad_pnc']:,.0f}</td>
            </tr>"""

        # Recomendaciones
        top3_dmg = df_exp.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum"),crit=("criticidad","sum")).sort_values("crit",ascending=False).head(3).reset_index()
        reco_html = ""
        for _, r in top3_dmg.iterrows():
            kbE = KB.get(r["damage"], {})
            s = r["std"]
            border = "#c0392b" if s=="D" else "#c9840a" if s=="C" else "#2d6b3f"
            bg = "#fdf0ef" if s=="D" else "#fef9ed" if s=="C" else "#e8f5ec"
            icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
            causa = kbE.get("causas",[""])[0] if kbE.get("causas") else ""
            sol   = kbE.get("soluciones",[""])[0] if kbE.get("soluciones") else ""
            proc_recs = KB.get("_process_recs",{}).get(r["damage"],{})
            proc_rec  = proc_recs.get(proc_e,"") if proc_e else ""
            txt = f"{r['pnc']:,.0f} PNC."
            if causa: txt += f" Causa frecuente: {causa}."
            if sol:   txt += f" {sol}."
            if proc_rec: txt += f" {proc_rec}"
            reco_html += f"""<div style="background:{bg};border-left:3px solid {border};
                padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0">
                <div style="font-weight:600;font-size:12px;margin-bottom:3px">{icon} {r['damage']}</div>
                <div style="font-size:11px;color:#444;line-height:1.5">{txt}</div>
            </div>"""

        # FULL HTML POSTER
        prov_title = prov_exp.replace("SERVIPINTARTE","SERVI<em>PINTARTE</em>").replace("INTERAUTOS","INTER<em>AUTOS</em>")
        is_servi = "SERVI" in prov_exp
        dark = "#0f2718" if is_servi else "#0d1f35" if "INTER" in prov_exp else "#1a1a2e"
        dark2 = "#1a3d25" if is_servi else "#162d4f" if "INTER" in prov_exp else "#2d2d4a"
        accent = "#3a8a51" if is_servi else "#2d65aa" if "INTER" in prov_exp else "#5a5a9a"
        light2 = "#7dca92" if is_servi else "#7aaee0" if "INTER" in prov_exp else "#9a9add"

        html_poster = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,*{{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
body{{background:#e8e8e6;font-family:'DM Sans',sans-serif;font-weight:300;padding:28px 40px;color:#111}}
.poster{{max-width:960px;margin:0 auto;display:grid;gap:16px;background:#faf8f3;padding:32px;border-radius:16px;box-shadow:0 4px 32px rgba(0,0,0,.08)}}
.header{{background:{dark};border-radius:12px;padding:28px 36px;display:grid;grid-template-columns:1fr auto;align-items:end;gap:20px}}
.hlabel{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:{light2};text-transform:uppercase;margin-bottom:6px}}
.htitle{{font-family:'DM Serif Display',serif;font-size:2rem;color:#fff;line-height:1.1}}
.htitle em{{color:{light2};font-style:italic}}
.hsub{{font-size:12px;color:{light2};margin-top:6px}}
.kpis{{display:flex;gap:20px;text-align:right}}
.kpi{{display:flex;flex-direction:column;align-items:flex-end}}
.kval{{font-family:'DM Serif Display',serif;font-size:1.8rem;color:#fff;line-height:1}}
.klbl{{font-size:10px;color:#7dca92;letter-spacing:.08em;text-transform:uppercase;margin-top:3px}}
.kdiv{{width:1px;background:rgba(255,255,255,.15);align-self:stretch}}
.std-band{{background:{dark2};border-radius:8px;padding:14px 24px;display:grid;grid-template-columns:auto 1fr 1fr 1fr;align-items:center;gap:0}}
.stdlbl{{font-family:'DM Mono',monospace;font-size:10px;color:{light2};text-transform:uppercase;padding-right:20px;border-right:1px solid rgba(255,255,255,.1);white-space:nowrap}}
.std-item{{display:flex;align-items:center;gap:10px;padding:0 16px;border-right:1px solid rgba(255,255,255,.1)}}
.std-item:last-child{{border-right:none}}
.stdnum{{font-family:'DM Serif Display',serif;font-size:1.5rem;color:#fff}}
.stdinf{{display:flex;flex-direction:column}}
.badge{{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-block;margin-bottom:2px}}
.bD{{background:#fde8e8;color:#c0392b}}.bC{{background:#fef3d0;color:#b7760a}}.bT{{background:#e8f5ec;color:#2d6b3f}}
.stdpct{{font-size:11px;color:{light2}}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.three-col{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}}
.card{{background:#fff;border-radius:10px;padding:18px 20px;border:1px solid rgba(0,0,0,.06)}}
.card-title{{font-family:'DM Serif Display',serif;font-size:.95rem;color:#0f1520;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #f0ece2}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;font-size:11px;color:#8a9e8e;font-weight:500;padding:0 10px 8px;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #f0ece2}}
.footer{{display:flex;justify-content:space-between;align-items:center;padding:12px 0 0;border-top:1px solid #f0ece2}}
.fbrand{{font-family:'DM Serif Display',serif;font-size:.95rem;color:{accent}}}
.fmeta{{font-family:'DM Mono',monospace;font-size:10px;color:#8a9e8e;text-align:right}}
.print-btn{{display:flex;align-items:center;justify-content:center;gap:8px;background:{dark};color:#fff;border:none;border-radius:8px;padding:12px 28px;font-family:'DM Sans',sans-serif;font-size:14px;font-weight:500;cursor:pointer;margin:0 auto 20px;transition:opacity .2s;width:fit-content}}
.print-btn:hover{{opacity:.85}}
@media print{{.print-btn{{display:none!important}}body{{padding:0;background:#faf8f3!important}}.poster{{box-shadow:none!important;border-radius:0!important;padding:16px!important}}}}
</style></head><body>

<button class="print-btn" onclick="window.print()">
  ⬇️ Descargar como PDF
</button>

<div class="poster">

<header class="header">
  <div>
    <div class="hlabel">Análisis de Calidad — Pintura · AKT Motos</div>
    <h1 class="htitle">{prov_title}</h1>
    <p class="hsub">Período: {periodo_label} &nbsp;·&nbsp; {proc_lbl_e}</p>
  </div>
  <div class="kpis">
    <div class="kpi"><span class="kval">{tot_e:,.0f}</span><span class="klbl">PNC Totales</span></div>
    <div class="kdiv"></div>
    <div class="kpi"><span class="kval">{avg_e:,.0f}</span><span class="klbl">Prom. mensual</span></div>
    <div class="kdiv"></div>
    <div class="kpi"><span class="kval">{pctD_e:.0f}%</span><span class="klbl">Dev. directa</span></div>
  </div>
</header>

<div class="std-band">
  <span class="stdlbl">STD-001</span>
  <div class="std-item">
    <span class="stdnum">{df_exp[df_exp['std']=='D']['cantidad_pnc'].sum():,.0f}</span>
    <div class="stdinf"><span class="badge bD">Devolución directa</span><span class="stdpct">{pctD_e:.0f}% del total</span></div>
  </div>
  <div class="std-item">
    <span class="stdnum">{df_exp[df_exp['std']=='C']['cantidad_pnc'].sum():,.0f}</span>
    <div class="stdinf"><span class="badge bC">Condicional</span><span class="stdpct">{pctC_e:.0f}% del total</span></div>
  </div>
  <div class="std-item">
    <span class="stdnum">{df_exp[df_exp['std']=='T']['cantidad_pnc'].sum():,.0f}</span>
    <div class="stdinf"><span class="badge bT">Tolerable</span><span class="stdpct">{pctT_e:.0f}% del total</span></div>
  </div>
</div>

<div class="two-col">
  <div class="card">
    <div class="card-title">Top 5 defectos por criticidad</div>
    <img src="data:image/png;base64,{def_img}" style="width:100%;border-radius:4px"/>
    <table style="margin-top:10px">
      <tr><th>Defecto</th><th>STD</th><th style="text-align:right">PNC</th><th style="text-align:right">%</th></tr>
      {std_rows}
    </table>
  </div>
  <div class="card">
    <div class="card-title">Distribución STD-001</div>
    <img src="data:image/png;base64,{pie_img}" style="width:100%;border-radius:4px"/>
    <div style="margin-top:10px">
      <div class="card-title" style="margin-top:8px">Top 5 piezas críticas</div>
      <table>
        <tr><th>#</th><th>Pieza</th><th style="text-align:right">PNC</th></tr>
        {pie_rows}
      </table>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-title">Tendencia mensual de PNC</div>
  <img src="data:image/png;base64,{trend_img}" style="width:100%;border-radius:4px"/>
</div>

<div class="card">
  <div class="card-title">💡 Acciones sugeridas</div>
  {reco_html}
</div>

<footer class="footer">
  <span class="fbrand">AKT Motos · Área de Desarrollo de Producto</span>
  <div class="fmeta">
    <div>Modelo de Análisis y Priorización de Defectos de Pintura</div>
    <div>Valentina Perdomo Perdomo · Ingeniería de Diseño de Producto</div>
  </div>
</footer>
</div>
</body></html>"""

        st.success(f"✅ Resumen listo para {prov_exp}")
        st.download_button(
            label="⬇️ Descargar resumen (abrir en navegador → PDF)",
            data=html_poster,
            file_name=f"Resumen_{prov_exp}_{periodo_label.replace(' ','_')}.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
        st.caption("💡 Al abrir el archivo descargado, usa el botón 'Descargar como PDF' o Ctrl+P → Guardar como PDF")

        # Preview
        with st.expander("👁️ Vista previa del resumen"):
            st.components.v1.html(html_poster, height=800, scrolling=True)

# ── TAB GESTIÓN DE PERÍODOS ────────────────────────────────────
with tab_mgmt:
    st.markdown('<div class="sec-title">Períodos guardados</div>', unsafe_allow_html=True)
    st.caption("Aquí puedes ver y eliminar períodos. Los períodos eliminados no aparecerán en ningún análisis.")

    all_p = get_periodos()
    if all_p.empty:
        st.info("No hay períodos guardados")
    else:
        for _, row in all_p.iterrows():
            col1, col2, col3, col4 = st.columns([3,2,2,1])
            col1.markdown(f"**{row['nombre']}**")
            col2.caption(f"📅 {row['fecha_carga']}")
            col3.caption(f"📋 {row['registros']:,} registros")
            if col4.button("🗑️", key=f"del_{row['id']}", help="Eliminar período"):
                con = sqlite3.connect(DB_PATH)
                con.execute("DELETE FROM registros WHERE periodo_id=?", (row['id'],))
                con.execute("DELETE FROM acciones WHERE periodo_id=?", (row['id'],))
                con.execute("DELETE FROM periodos WHERE id=?", (row['id'],))
                con.commit(); con.close()
                st.success(f"✅ {row['nombre']} eliminado")
                st.rerun()

        st.markdown("")
        st.caption(f"Total: {len(all_p)} período(s) guardado(s)")

# ── TAB ACCIONES ─────────────────────────────────────────────
with tab_acc:
    st.markdown('<div class="sec-title">Registrar nueva acción</div>', unsafe_allow_html=True)
    with st.form("form_acc"):
        fa1,fa2 = st.columns(2)
        with fa1:
            ac_per  = fa1.selectbox("Período", list(periodo_options.keys()))
            ac_prov = fa1.selectbox("Proveedor", sorted(df["proveedor"].unique()))
            ac_dmg  = fa1.selectbox("Defecto", ["—"]+sorted(df["damage"].dropna().unique().tolist()))
        with fa2:
            ac_resp  = fa2.text_input("Responsable")
            ac_fecha = fa2.date_input("Fecha de compromiso")
            ac_est   = fa2.selectbox("Estado",["Pendiente","En proceso","Completada","Cancelada"])
        ac_acc  = st.text_area("Acción", height=70)
        ac_nota = st.text_area("Notas", height=50)
        if st.form_submit_button("💾 Guardar",use_container_width=True) and ac_acc:
            save_accion(periodo_options[ac_per],ac_prov,
                ac_dmg if ac_dmg!="—" else "",
                ac_acc,ac_resp,str(ac_fecha),ac_est,ac_nota)
            st.success("✅ Acción guardada"); st.rerun()

    st.markdown('<div class="sec-title">Seguimiento de acciones</div>', unsafe_allow_html=True)
    ff1,ff2 = st.columns(2)
    fil_prov = ff1.selectbox("Proveedor",["Todos"]+sorted(df["proveedor"].unique().tolist()),key="fil_p")
    fil_est  = ff2.selectbox("Estado",["Todos","Pendiente","En proceso","Completada","Cancelada"])

    acc_df = get_acciones(fil_prov if fil_prov!="Todos" else None)
    if fil_est!="Todos": acc_df = acc_df[acc_df["estado"]==fil_est]

    if acc_df.empty:
        st.info("Sin acciones registradas")
    else:
        for _,ac in acc_df.iterrows():
            est = ac["estado"]
            css = "ac-done" if est=="Completada" else "ac-pend"
            icon = {"Pendiente":"⏳","En proceso":"🔄","Completada":"✅","Cancelada":"❌"}.get(est,"⏳")
            st.markdown(f'<div class="{css}"><strong>{icon} {ac["proveedor"]}</strong> — {ac["defecto"] or "General"} <span style="float:right;font-size:.75rem;color:#888">{ac["fecha_creacion"]} · {ac["periodo_nombre"]}</span><br><span style="font-size:.85rem">{ac["accion"]}</span><br><span style="font-size:.75rem;color:#666">Resp: {ac["responsable"] or "—"} · Compromiso: {ac["fecha_compromiso"] or "—"} · {est}</span></div>', unsafe_allow_html=True)
            if est not in ["Completada","Cancelada"]:
                b1,b2,_ = st.columns([1,1,4])
                if b1.button("✅ Completar",key=f"c{ac['id']}"):
                    update_accion(ac["id"],"Completada"); st.rerun()
                if b2.button("🔄 En proceso",key=f"p{ac['id']}"):
                    update_accion(ac["id"],"En proceso"); st.rerun()
