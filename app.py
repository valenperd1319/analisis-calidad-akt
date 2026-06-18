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

KB = {'Tallado': {'tipo': 'Pintura', 'desc': 'Marcas superficiales en la pintura por contacto físico', 'causas': ['Manipulación sin guantes post-horno', 'Apilamiento sin separadores', 'Superficies de trabajo con bordes filosos', 'Embalaje inadecuado'], 'soluciones': ['Usar guantes de algodón en toda la cadena post-horno', 'Implementar separadores de espuma entre piezas', 'Revisar puntos de contacto en línea de producción', 'Establecer zonas de almacenamiento con soportes acolchados'], 'std': 'T', 'urgencia': 2}, 'Grumo': {'tipo': 'Pintura', 'desc': 'Partículas o protuberancias en la superficie mayores a 0.3mm', 'causas': ['Filtros de cabina saturados', 'Pintura sin colar antes de aplicar', 'Boquilla desgastada', 'Presión de atomización incorrecta', 'Temperatura de cabina muy alta'], 'soluciones': ['Cambiar filtros cada 100 horas o 3-4 semanas', 'Colar pintura con malla 100-150 micras', 'Verificar presión 1.5-2 bar en HVLP', 'Reemplazar boquillas mensualmente', 'Mantener cabina 20-25°C'], 'std': 'C', 'urgencia': 4}, 'Rayado': {'tipo': 'Pintura', 'desc': 'Arañazos que pueden llegar al sustrato', 'causas': ['Manipulación sin guantes o con materiales abrasivos', 'Empaque sin protección', 'Roce durante ensamble'], 'soluciones': ['Protocolo obligatorio de guantes de algodón', 'Bolsas o fundas de tela por pieza', 'Revisar puntos de contacto en línea de ensamble'], 'std': 'D', 'urgencia': 5}, 'Adherencia': {'tipo': 'Pintura', 'desc': 'Falta de anclaje de la pintura al sustrato', 'causas': ['Superficie contaminada con grasa o aceite', 'Omisión del promotor de adhesión en ABS/PP', 'Humedad en la superficie', 'Alta humedad ambiental en Colombia'], 'soluciones': ['Lavar con desengrasante antes de cada pieza', 'Aplicar promotor en piezas de ABS y PP (5-10 min oreo)', 'Verificar sustrato completamente seco', 'Controlar humedad relativa 40-60% en cabina'], 'std': 'D', 'urgencia': 5, 'colombia_note': 'En Colombia la alta humedad especialmente en temporadas de lluvia es un factor crítico. Usar catalizadores adaptados al clima tropical.'}, 'Ojo de pez': {'tipo': 'Pintura', 'desc': 'Cráteres circulares por contaminación con silicona o aceite', 'causas': ['Aire comprimido contaminado con aceite', 'Trapos con residuos de silicona', 'Productos con silicona cerca de la cabina'], 'soluciones': ['Instalar separador de agua y aceite en la línea de aire', 'Prohibir productos con silicona en el área', 'Limpiar cabina con desengrasante semanalmente'], 'std': 'C', 'urgencia': 3}, 'Diferente tono': {'tipo': 'Pintura', 'desc': 'Variación de color respecto a la probeta aprobada', 'causas': ['Mezcla incorrecta o diferente lote de pigmento', 'Variaciones de temperatura en el horno', 'Tiempo de mezcla insuficiente'], 'soluciones': ['Verificar número de lote antes de producción', 'Calibrar temperatura del horno periódicamente', 'Agitar la pintura mínimo 5 minutos antes de aplicar'], 'std': 'D', 'urgencia': 4}, 'Micro hervido': {'tipo': 'Pintura', 'desc': 'Pequeñas burbujas por disolventes atrapados', 'causas': ['Temperatura muy alta que seca la superficie antes del interior', 'Diluyente demasiado lento', 'Capas muy gruesas', 'Alta temperatura + humedad en Colombia'], 'soluciones': ['Usar diluyentes apropiados a la temperatura del día', 'Respetar tiempos de flash-off entre capas', 'Aplicar capas más delgadas', 'Controlar temperatura de cabina 20-25°C'], 'std': 'C', 'urgencia': 3, 'colombia_note': 'En ciudades de clima cálido ajustar el catalizador según recomendación del fabricante.'}, 'Pintura chorreada': {'tipo': 'Pintura', 'desc': 'Escurrimientos en superficies inclinadas', 'causas': ['Exceso de pintura en una pasada', 'Diluyente demasiado lento', 'Distancia de pistola muy corta'], 'soluciones': ['Aplicar capas más delgadas', 'Calibrar presión caudal y abanico', 'Mantener distancia constante 20-30 cm'], 'std': 'D', 'urgencia': 4}, 'Faltante de pintura': {'tipo': 'Pintura', 'desc': 'Zonas sin cobertura de pintura', 'causas': ['Boquilla tapada', 'Velocidad de aplicación alta', 'Presión insuficiente'], 'soluciones': ['Verificar boquilla antes de producción', 'Establecer revisión de todas las caras al salir del horno', 'Calibrar presión al inicio de cada turno'], 'std': 'D', 'urgencia': 5}, 'Hundido': {'tipo': 'Pintura', 'desc': 'Deformación o abolladura en la pieza', 'causas': ['Golpes durante manejo pre-pintado', 'Presión excesiva en herramentales', 'Impacto en transporte'], 'soluciones': ['Revisar piezas en recepción antes de ingresar al proceso', 'Usar soportes acolchados', 'Registrar piezas con defecto previo para trazabilidad'], 'std': 'D', 'urgencia': 5}, 'Piel naranja': {'tipo': 'Pintura', 'desc': 'Textura rugosa similar a piel de naranja', 'causas': ['Presión de atomización muy alta', 'Distancia de pistola muy grande', 'Diluyente muy rápido'], 'soluciones': ['Ajustar presión dentro del rango recomendado', 'Mantener distancia adecuada 20-30 cm', 'Usar diluyente apropiado a temperatura de trabajo'], 'std': 'C', 'urgencia': 2}, 'Oxidado': {'tipo': 'Pintura', 'desc': 'Corrosión del sustrato metálico', 'causas': ['Exposición a humedad sin protección', 'Falla en primer anticorrosivo', 'Almacenamiento inadecuado'], 'soluciones': ['Revisar proceso de imprimación y primer', 'Almacenar piezas metálicas en ambiente seco', 'Controlar tiempo entre preparación y pintado'], 'std': 'D', 'urgencia': 5}, 'Desprendimiento de pintura': {'tipo': 'Pintura', 'desc': 'La pintura se desprende en placas', 'causas': ['Falla grave de adherencia', 'Superficie contaminada con desmoldante', 'Curado incompleto'], 'soluciones': ['Verificar promotor en 100% de piezas plásticas', 'Revisar proceso de preparación de superficie', 'Confirmar temperatura y tiempo de curado'], 'std': 'D', 'urgencia': 5}, 'Defecto de pintura': {'tipo': 'Pintura', 'desc': 'Defecto genérico no clasificado', 'causas': ['Condiciones de cabina fuera de rango', 'Insumos con problemas de calidad'], 'soluciones': ['Clasificar el defecto para tomar acción correctiva', 'Revisar condiciones de cabina', 'Verificar calidad del lote en uso'], 'std': 'C', 'urgencia': 2}, 'Pintura contaminada': {'tipo': 'Pintura', 'desc': 'Pintura con partículas extrañas visibles', 'causas': ['Almacenamiento inadecuado', 'Recipientes sucios', 'Pintura vencida'], 'soluciones': ['Colar siempre la pintura antes de aplicar', 'Revisar condiciones de almacenamiento', 'Verificar fecha de vencimiento del lote'], 'std': 'C', 'urgencia': 3}, 'Pintura Levantada': {'tipo': 'Pintura', 'desc': 'La pintura se levanta en burbujas sin desprenderse', 'causas': ['Humedad atrapada debajo de la pintura', 'Temperatura de horno genera vapor', 'Capas muy gruesas'], 'soluciones': ['Sustrato completamente seco antes de pintar', 'Revisar temperatura de curado', 'Respetar tiempos de flash-off'], 'std': 'D', 'urgencia': 4}, 'Contaminado': {'tipo': 'Pintura', 'desc': 'Partículas externas incrustadas en la pintura', 'causas': ['Corrientes de aire con polvo en cabina', 'Personal sin indumentaria adecuada', 'Filtros saturados'], 'soluciones': ['Limpiar cabina al inicio de cada turno', 'Usar indumentaria antiestática', 'Verificar filtros semanalmente'], 'std': 'C', 'urgencia': 3}, 'Golpeado': {'tipo': 'Averias MP', 'desc': 'Golpe o impacto visible en la pieza', 'causas': ['Manipulación inadecuada durante transporte o almacenamiento', 'Embalaje insuficiente para proteger la pieza', 'Caída durante el proceso de ensamble'], 'soluciones': ['Mejorar el embalaje individual de piezas sensibles', 'Revisar procedimientos de manipulación en bodega y línea', 'Capacitar al personal en manejo cuidadoso de piezas'], 'std': 'D', 'urgencia': 4}, 'Roto': {'tipo': 'Sillas', 'desc': 'Ruptura en estructura, tapizado o espuma del asiento', 'causas': ['Espuma de densidad insuficiente', 'Material de tapizado con baja resistencia', 'Grapas mal colocadas', 'Impacto durante manipulación'], 'soluciones': ['Verificar densidad de espuma mínimo 35 kg/m³', 'Revisar proceso de grapeado y tensado', 'Prueba de carga estática por lote', 'Mejorar embalaje para transporte'], 'std': 'D', 'urgencia': 5}, 'Falta buje': {'tipo': 'Sillas', 'desc': 'Ausencia del buje de sujeción del sillín', 'causas': ['Omisión en proceso de ensamble', 'Error en kit de piezas del proveedor'], 'soluciones': ['Verificación final de componentes antes del empaque', 'Implementar checklist visual por referencia'], 'std': 'D', 'urgencia': 5}, 'Base sillín no conforme': {'tipo': 'Sillas', 'desc': 'Base del sillín fuera de especificaciones', 'causas': ['Molde desgastado o fuera de calibración', 'Material de inyección diferente a especificación'], 'soluciones': ['Verificar dimensiones contra plano aprobado en recepción', 'Solicitar certificado de material por lote'], 'std': 'D', 'urgencia': 4}, 'Desgrapado de Silla': {'tipo': 'Sillas', 'desc': 'Tapizado se desprende por fallas en el grapeado', 'causas': ['Grapas de calibre insuficiente', 'Tensado incorrecto del tapizado', 'Proceso de grapeado sin control'], 'soluciones': ['Estandarizar calibre y tipo de grapa', 'Capacitar en técnica correcta de tensado', 'Prueba de jalado como control en proceso'], 'std': 'D', 'urgencia': 4}, 'Incompleto': {'tipo': 'Averias MP', 'desc': 'Pieza con componentes o partes faltantes', 'causas': ['Omisión en el proceso de ensamble o empaque', 'Error en el kit de piezas suministrado', 'Falta de verificación final antes de despacho'], 'soluciones': ['Checklist de componentes por referencia antes del empaque', 'Verificación visual o por peso al final de línea', 'Revisar el proceso de picking del proveedor'], 'std': 'D', 'urgencia': 4}, 'Deforme': {'tipo': 'Sillas', 'desc': 'Forma del sillín diferente a especificación', 'causas': ['Espuma con densidad incorrecta', 'Almacenamiento incorrecto que genera deformación'], 'soluciones': ['Verificar forma contra muestra aprobada por lote', 'Revisar condiciones de almacenamiento'], 'std': 'C', 'urgencia': 3}, 'Ruido interno': {'tipo': 'Sillas', 'desc': 'Ruido o crujido al ejercer presión', 'causas': ['Componentes internos sueltos', 'Espuma que no cubre estructura interna'], 'soluciones': ['Prueba de presión manual en control de recepción', 'Verificar fijación de componentes internos'], 'std': 'C', 'urgencia': 3}, 'Falta platina': {'tipo': 'Sillas', 'desc': 'Ausencia de la platina metálica de sujeción', 'causas': ['Omisión en ensamble', 'Error en kit de componentes'], 'soluciones': ['Verificar componentes metálicos antes del empaque', 'Verificación por peso del conjunto'], 'std': 'D', 'urgencia': 5}, '_process_context': {'batch': {'nombre': 'Por lotes (horno cerrado)', 'riesgos': ['Variación de temperatura entre inicio y final del lote', 'Mayor manejo manual en carga y descarga']}, 'continuo': {'nombre': 'Línea continua (horno abierto)', 'riesgos': ['La puerta siempre abierta puede introducir partículas', 'Cambios de temperatura ambiental afectan el proceso']}}, '_process_recs': {'Grumo': {'batch': 'En proceso por lotes verificar que la temperatura esté estabilizada antes de cargar piezas y colar la pintura antes de cada lote.', 'continuo': 'En línea continua revisar si hay fuentes de polvo cerca de la entrada del túnel y aumentar frecuencia de revisión de filtros.'}, 'Micro hervido': {'batch': 'Revisar la uniformidad de temperatura dentro del horno y la rampa de calentamiento entre ciclos.', 'continuo': 'Verificar el tiempo de tránsito de las piezas por cada zona y que la velocidad de línea permita el aireado correcto.'}, 'Diferente tono': {'batch': 'Los primeros lotes del día pueden tener variación porque el horno no ha estabilizado temperatura. Esperar estabilización antes de producción de primera calidad.', 'continuo': 'Las variaciones aparecen al inicio y final de jornada. Establecer tiempo de estabilización de línea antes de producir.'}, 'Adherencia': {'batch': 'Asegurar que las piezas estén completamente secas antes de cargar el lote. El horno cerrado puede concentrar humedad residual.', 'continuo': 'En días lluviosos en Colombia la humedad que entra por la apertura del túnel puede afectar el curado. Ajustar catalizador en temporada de lluvias.'}, 'Ojo de pez': {'batch': 'Generalmente viene de contaminación en pistola o pintura. Revisar sistema de aire comprimido y limpieza de pistola antes de cada lote.', 'continuo': 'Puede venir de contaminación que entra por la apertura del túnel. Considerar cortina de aire en la entrada.'}, 'Tallado': {'batch': 'El mayor riesgo es en la carga y descarga manual del horno. Implementar protocolo específico con guantes y superficies acolchadas en esos momentos.', 'continuo': 'Revisar todos los puntos de contacto del transportador y protegerlos con materiales blandos.'}}, '_provider_process': {'SERVIPINTARTE': 'batch', 'INTERAUTOS': 'continuo'}, 'Reventado': {'tipo': 'Averias MP', 'desc': 'Ruptura o estallido de la pieza, generalmente por fragilidad o sobrepresión', 'causas': ['Material plástico con fragilidad por temperatura de inyección incorrecta', 'Espesor de pared insuficiente para la carga que debe soportar', 'Tensión interna acumulada durante el moldeo por enfriamiento desigual', 'Impacto durante manipulación o transporte'], 'soluciones': ['Verificar la temperatura de inyección según ficha técnica del material', 'Revisar el diseño de espesor de pared con el proveedor', 'Solicitar inspección de tensión interna en piezas críticas', 'Mejorar el embalaje para reducir impactos en transporte'], 'std': 'D', 'urgencia': 5}, 'Rosca rodada': {'tipo': 'Averias MP', 'desc': 'La rosca pierde su forma o filete, generalmente por exceso de torque', 'causas': ['Apriete con torque superior al especificado', 'Herramienta de atornillado sin control de torque (no calibrada)', 'Material de la rosca más blando de lo necesario para la aplicación', 'Tornillo insertado torcido o desalineado'], 'soluciones': ['Usar torquímetro calibrado en el proceso de ensamble', 'Establecer el valor de torque específico por tipo de tornillo y material', 'Capacitar al personal en la técnica correcta de atornillado', 'Verificar alineación del tornillo antes de aplicar torque final'], 'std': 'D', 'urgencia': 4}, 'Daño en pieza': {'tipo': 'Averias MP', 'desc': 'Daño genérico no clasificado en otra categoría específica', 'causas': ['Múltiples causas posibles — requiere clasificación más específica', 'Manipulación inadecuada', 'Defecto de fabricación del proveedor'], 'soluciones': ['Clasificar el tipo de daño específico para acción correctiva concreta', 'Revisar con el proveedor el origen del defecto', 'Inspeccionar el lote de origen para detectar patrones'], 'std': 'C', 'urgencia': 3}, 'Rosca mala': {'tipo': 'Averias MP', 'desc': 'Rosca mal fabricada desde origen, no se ajusta correctamente al tornillo', 'causas': ['Macho o matriz de roscado desgastado o mal calibrado', 'Proceso de corte de rosca con tolerancias incorrectas', 'Falta de inspección de calidad en el proveedor antes del envío'], 'soluciones': ['Solicitar al proveedor verificación con calibrador de rosca por lote', 'Revisar el mantenimiento de las herramientas de corte del proveedor', 'Establecer inspección de roscas en la recepción de piezas críticas'], 'std': 'D', 'urgencia': 4}, 'No encaja pieza': {'tipo': 'Averias MP', 'desc': 'La pieza no ajusta correctamente con su contraparte en el ensamble', 'causas': ['Variación dimensional fuera de tolerancia', 'Molde desgastado que genera piezas fuera de especificación', 'Diferencias entre lotes de diferentes proveedores o fechas'], 'soluciones': ['Verificar dimensiones críticas contra el plano en recepción', 'Solicitar certificado dimensional por lote al proveedor', 'Realizar prueba de ensamble en muestra antes de aprobar el lote'], 'std': 'D', 'urgencia': 4}, 'Torcido': {'tipo': 'Averias MP', 'desc': 'Deformación o alabeo de la pieza respecto a su forma original', 'causas': ['Enfriamiento desigual durante el proceso de inyección', 'Tiempo de enfriamiento insuficiente antes de la expulsión del molde', 'Tensión interna por parámetros de inyección incorrectos', 'Almacenamiento inadecuado que genera deformación con el tiempo'], 'soluciones': ['Revisar el tiempo de enfriamiento en el proceso de inyección del proveedor', 'Verificar condiciones de almacenamiento (temperatura, apilamiento)', 'Solicitar ajuste de parámetros de inyección si el problema persiste'], 'std': 'C', 'urgencia': 3}, 'Tornillo Rodado': {'tipo': 'Averias MP', 'desc': 'El tornillo pierde su rosca o filete por desgaste o mal uso', 'causas': ['Apriete con torque excesivo', 'Reutilización de tornillos ya desgastados', 'Herramienta de atornillado inadecuada para el tipo de tornillo'], 'soluciones': ['Usar tornillos nuevos en cada ensamble, no reutilizar', 'Calibrar el torque según especificación técnica', 'Verificar que la herramienta coincida con el tipo de cabeza del tornillo'], 'std': 'C', 'urgencia': 3}, 'Exceso de pintura': {'tipo': 'Averias MP', 'desc': 'Capa de pintura más gruesa de lo especificado, puede afectar ensamble', 'causas': ['Múltiples pasadas de pistola sin control de espesor', 'Calibración incorrecta del caudal de pintura'], 'soluciones': ['Verificar espesor de capa con medidor durante el proceso', 'Calibrar el caudal de la pistola según ficha técnica'], 'std': 'C', 'urgencia': 2}, 'Mala medida': {'tipo': 'Averias MP', 'desc': 'Pieza fuera de las dimensiones especificadas en el plano', 'causas': ['Molde desgastado o fuera de calibración', 'Contracción del material diferente a la esperada', 'Variación en parámetros de inyección entre lotes'], 'soluciones': ['Verificar dimensiones críticas contra plano en cada lote', 'Solicitar reporte dimensional al proveedor', 'Revisar mantenimiento y calibración del molde'], 'std': 'D', 'urgencia': 4}, 'Defecto de cromo': {'tipo': 'Averias MP', 'desc': 'Falla en el recubrimiento cromado de la pieza (manchas, falta de brillo, desprendimiento)', 'causas': ['Preparación de superficie insuficiente antes del cromado', 'Concentración o temperatura del baño de cromo fuera de rango', 'Contaminación de la superficie antes del proceso'], 'soluciones': ['Verificar el proceso de preparación de superficie del proveedor', 'Solicitar certificado de control de baño de cromo', 'Inspeccionar visualmente el 100% de piezas cromadas en recepción'], 'std': 'D', 'urgencia': 4}, 'Tornillo reventado': {'tipo': 'Averias MP', 'desc': 'El tornillo se rompe durante el apriete o uso', 'causas': ['Material del tornillo de baja calidad o resistencia insuficiente', 'Torque aplicado superior a la capacidad del tornillo', 'Tornillo con defecto de fabricación previo'], 'soluciones': ['Verificar especificación de resistencia del tornillo con el proveedor', 'Usar torquímetro calibrado y respetar el valor especificado', 'Inspeccionar visualmente tornillos antes de usar en ensamble crítico'], 'std': 'D', 'urgencia': 4}, 'Neumático chuzado': {'tipo': 'Averias MP', 'desc': 'Perforación en el neumático que afecta su función', 'causas': ['Defecto de fabricación del neumático', 'Daño durante transporte o almacenamiento', 'Manipulación inadecuada con objetos punzantes cerca'], 'soluciones': ['Inspeccionar neumáticos en recepción antes de montar', 'Revisar condiciones de almacenamiento (libre de objetos punzantes)', 'Reportar al proveedor para análisis de causa raíz'], 'std': 'D', 'urgencia': 4}, 'Mal funcionamiento': {'tipo': 'Averias MP', 'desc': 'La pieza no cumple su función mecánica o eléctrica esperada', 'causas': ['Defecto de ensamble interno del componente', 'Falla de un componente eléctrico o mecánico interno', 'Conexión incorrecta durante el ensamble'], 'soluciones': ['Realizar prueba funcional al 100% antes de instalar en la moto', 'Reportar al proveedor para análisis de causa raíz', 'Verificar el proceso de conexión y ensamble del componente'], 'std': 'D', 'urgencia': 4}, 'Canibalizado': {'tipo': 'Averias MP', 'desc': 'A la pieza le falta un componente porque fue retirado para usarlo en otra unidad', 'causas': ['Práctica de retirar piezas de unidades en proceso para resolver faltantes urgentes', 'Falta de control de inventario que generó faltante original'], 'soluciones': ['Evitar la práctica de canibalización — generar orden de faltante en su lugar', 'Mejorar el control de inventario de componentes críticos', 'Registrar y dar seguimiento a la causa raíz del faltante original'], 'std': 'D', 'urgencia': 3}, 'Rosca rodada L3': {'tipo': 'Averias MP', 'desc': 'Rosca dañada por exceso de torque en proceso L3', 'causas': ['Apriete con torque superior al especificado', 'Herramienta sin control de torque'], 'soluciones': ['Usar torquímetro calibrado', 'Establecer valor de torque específico por tipo de tornillo'], 'std': 'D', 'urgencia': 4}, 'Orificio defectuoso': {'tipo': 'Averias MP', 'desc': 'Orificio de la pieza fuera de especificación, mal ubicado o con rebabas', 'causas': ['Desgaste del molde o herramienta de perforación', 'Posicionamiento incorrecto en el proceso de fabricación'], 'soluciones': ['Verificar dimensiones y posición del orificio contra plano', 'Revisar mantenimiento de herramientas de perforación del proveedor'], 'std': 'D', 'urgencia': 4}, 'Esparrago rodado': {'tipo': 'Averias MP', 'desc': 'El esparrago pierde su rosca por desgaste o mal uso', 'causas': ['Torque excesivo durante el ensamble', 'Esparrago de material o calidad insuficiente'], 'soluciones': ['Usar torquímetro calibrado', 'Verificar especificación de material con el proveedor'], 'std': 'C', 'urgencia': 3}, 'Esparrago reventado': {'tipo': 'Averias MP', 'desc': 'El esparrago se rompe durante el apriete o uso', 'causas': ['Material de baja resistencia', 'Torque excesivo aplicado durante el ensamble'], 'soluciones': ['Verificar especificación de resistencia con el proveedor', 'Respetar el valor de torque especificado con torquímetro'], 'std': 'D', 'urgencia': 4}, 'Caucho roto': {'tipo': 'Averias MP', 'desc': 'Pieza de caucho rota o fracturada', 'causas': ['Material de caucho de baja calidad o envejecido', 'Exposición a condiciones que degradan el caucho (calor, sol, químicos)', 'Instalación incorrecta que genera tensión excesiva'], 'soluciones': ['Verificar fecha de fabricación y vida útil del caucho con el proveedor', 'Revisar condiciones de almacenamiento del componente', 'Verificar el proceso de instalación para evitar tensión excesiva'], 'std': 'D', 'urgencia': 4}, 'fallas de funcionamiento': {'tipo': 'Averias MP', 'desc': 'La pieza no cumple su función esperada de forma intermitente o total', 'causas': ['Defecto interno del componente', 'Conexión o ensamble incorrecto'], 'soluciones': ['Prueba funcional al 100% antes de instalación', 'Reportar al proveedor para análisis de causa raíz'], 'std': 'D', 'urgencia': 4}, 'Falta tuerca': {'tipo': 'Averias MP', 'desc': 'Ausencia de la tuerca de sujeción en el kit de la pieza', 'causas': ['Omisión en el proceso de empaque del kit', 'Error en el conteo de componentes del proveedor'], 'soluciones': ['Checklist de componentes del kit antes de despacho', 'Verificación por peso del conjunto completo'], 'std': 'D', 'urgencia': 5}, 'Falta tornillo': {'tipo': 'Averias MP', 'desc': 'Ausencia del tornillo de sujeción en el kit de la pieza', 'causas': ['Omisión en el proceso de empaque del kit', 'Error en el conteo de componentes del proveedor'], 'soluciones': ['Checklist de componentes del kit antes de despacho', 'Verificación por peso del conjunto completo'], 'std': 'D', 'urgencia': 5}, 'Falta abrazadera': {'tipo': 'Averias MP', 'desc': 'Ausencia de la abrazadera de sujeción en el kit', 'causas': ['Omisión en el proceso de empaque del kit', 'Error en el conteo de componentes del proveedor'], 'soluciones': ['Checklist de componentes del kit antes de despacho', 'Verificación por peso del conjunto completo'], 'std': 'D', 'urgencia': 5}, 'Cable reventado': {'tipo': 'Averias MP', 'desc': 'Cable eléctrico o mecánico roto', 'causas': ['Material de baja resistencia o calidad', 'Tensión excesiva durante instalación o uso', 'Defecto de fabricación previo'], 'soluciones': ['Verificar especificación de resistencia con el proveedor', 'Revisar el proceso de instalación para evitar tensión excesiva'], 'std': 'D', 'urgencia': 4}, 'Parte Equivocada': {'tipo': 'Averias MP', 'desc': 'Se envió o instaló una pieza diferente a la especificada', 'causas': ['Error en el picking o preparación del pedido del proveedor', 'Confusión entre referencias similares', 'Etiquetado incorrecto del lote'], 'soluciones': ['Verificar referencia contra orden de compra en recepción', 'Mejorar el etiquetado y separación física de referencias similares', 'Establecer doble verificación en el picking del proveedor'], 'std': 'D', 'urgencia': 4}, 'Rosca mala L3': {'tipo': 'Averias MP', 'desc': 'Rosca mal fabricada desde origen en proceso L3', 'causas': ['Macho o matriz de roscado desgastado', 'Proceso de corte con tolerancias incorrectas'], 'soluciones': ['Verificación con calibrador de rosca por lote', 'Revisar mantenimiento de herramientas de corte'], 'std': 'D', 'urgencia': 4}, 'Deterioro': {'tipo': 'Averias MP', 'desc': 'Desgaste o degradación visible de la pieza, generalmente por almacenamiento prolongado', 'causas': ['Tiempo de almacenamiento excesivo antes de uso', 'Condiciones ambientales inadecuadas (humedad, calor, sol)'], 'soluciones': ['Implementar rotación de inventario FIFO (primero en entrar, primero en salir)', 'Revisar condiciones de almacenamiento de piezas sensibles'], 'std': 'C', 'urgencia': 3}, 'Mal pegada': {'tipo': 'Calcomanías', 'desc': 'La calcomanía no quedó correctamente adherida a la superficie', 'causas': ['Superficie con polvo, grasa o humedad al momento de pegar', 'Calcomanía con adhesivo de baja calidad o vencido', 'Presión insuficiente al momento de aplicar y fijar la calcomanía', 'Temperatura ambiente fuera de rango para el adhesivo'], 'soluciones': ['Limpiar la superficie con desengrasante antes de aplicar la calcomanía', 'Verificar fecha de fabricación y condiciones de almacenamiento del adhesivo', 'Usar rodillo o espátula para fijar con presión uniforme', 'Aplicar en un rango de temperatura ambiente de 18-25°C'], 'std': 'C', 'urgencia': 3}, 'Mal ubicado': {'tipo': 'Calcomanías', 'desc': 'La calcomanía está colocada en una posición incorrecta respecto al diseño aprobado', 'causas': ['Falta de plantilla o guía de posicionamiento en el puesto de trabajo', 'Error del operario al posicionar manualmente', 'Pieza base con variación dimensional que desplaza la referencia'], 'soluciones': ['Implementar plantilla física o láser guía para posicionamiento exacto', 'Capacitar al operario en el punto de referencia correcto', 'Verificar consistencia dimensional de la pieza base'], 'std': 'C', 'urgencia': 2}, 'Mal estado': {'tipo': 'Calcomanías', 'desc': 'Calcomanía dañada, rota o deteriorada antes o durante la instalación', 'causas': ['Daño durante el transporte o almacenamiento del proveedor', 'Manipulación inadecuada al momento de aplicar', 'Calcomanía de baja calidad que se daña fácilmente'], 'soluciones': ['Revisar el empaque del proveedor para mejor protección', 'Capacitar al operario en manipulación cuidadosa', 'Solicitar mejora de calidad de material al proveedor'], 'std': 'C', 'urgencia': 2}, 'Diferente Medida': {'tipo': 'Calcomanías', 'desc': 'Calcomanía con dimensiones distintas a la especificación aprobada', 'causas': ['Error de corte en el proceso de fabricación del proveedor', 'Variación entre lotes de producción'], 'soluciones': ['Verificar dimensiones contra ficha técnica en recepción por lote', 'Solicitar al proveedor control dimensional antes de envío'], 'std': 'D', 'urgencia': 3}, 'Falta calcomanía': {'tipo': 'Calcomanías', 'desc': 'Ausencia de la calcomanía en la pieza', 'causas': ['Omisión en el proceso de ensamble', 'Falta de control de piezas al final de línea'], 'soluciones': ['Checklist visual de componentes por referencia', 'Punto de control al final del proceso de ensamble'], 'std': 'D', 'urgencia': 4}}

WEIGHTS = {
    "Tallado":1,"Rayado":2,"Piel naranja":2,"Pintura tallada":2,
    "Diferente tono":2,"Diferente color":3,"Grumo":3,"Micro hervido":3,"Hundido":3,
    "Defecto de pintura":3,"Contaminado":3,"Pintura contaminada":3,"Textura defectuosa":3,
    "Ojo de pez":3,"Pintura chorreada":3,"Pintura Levantada":4,
    "Sin pintar":4,"Faltante de pintura":4,"Faltante":4,
    "Adherencia":5,"Desprendimiento de pintura":5,"Desprendimiento":5,
    "Oxidado":5,"Roto":5,"Reventado":5,"Golpeado":3,"Deforme":3,
    "Base sillín no conforme":4,"Desgrapado de Silla":4,"Incompleto":4,
    "Falta buje":5,"Falta platina":5,"Ruido interno":3,
    "Rosca rodada":4,"Daño en pieza":2,"Rosca mala":4,"No encaja pieza":4,
    "Torcido":3,"Tornillo Rodado":3,"Exceso de pintura":2,"Mala medida":4,
    "Defecto de cromo":4,"Tornillo reventado":4,"Neumático chuzado":4,
    "Mal funcionamiento":4,"Canibalizado":3,"Rosca rodada L3":4,
    "Orificio defectuoso":4,"Esparrago rodado":3,"Esparrago reventado":4,
    "Caucho roto":4,"fallas de funcionamiento":4,"Falta tuerca":5,
    "Falta tornillo":5,"Falta abrazadera":5,"Cable reventado":4,
    "Parte Equivocada":4,"Rosca mala L3":4,"Deterioro":3,
    "Mal pegada":2,"Mal ubicado":2,"Mal estado":2,"Diferente Medida":3,
    "Falta calcomanía":4,
}

STD = {
    "Adherencia":"D","Desprendimiento de pintura":"D","Desprendimiento":"D",
    "Pintura chorreada":"D","Rayado":"D","Faltante de pintura":"D","Sin pintar":"D",
    "Faltante":"D","Hundido":"D","Roto":"D","Reventado":"D","Diferente tono":"D",
    "Diferente color":"D","Pintura Levantada":"D","Oxidado":"D",
    "Falta buje":"D","Falta platina":"D","Incompleto":"D","Base sillín no conforme":"D",
    "Desgrapado de Silla":"D",
    "Grumo":"C","Micro hervido":"C","Ojo de pez":"C","Piel naranja":"C",
    "Contaminado":"C","Pintura contaminada":"C","Textura defectuosa":"C",
    "Pintura tallada":"C","Defecto de pintura":"C","Deforme":"C","Ruido interno":"C",
    "Tallado":"T","Marca de lija":"T","Mal masillado":"T","Golpeado":"D",
    "Rosca rodada":"D","Daño en pieza":"C","Rosca mala":"D","No encaja pieza":"D",
    "Torcido":"C","Tornillo Rodado":"C","Exceso de pintura":"C","Mala medida":"D",
    "Defecto de cromo":"D","Tornillo reventado":"D","Neumático chuzado":"D",
    "Mal funcionamiento":"D","Canibalizado":"D","Rosca rodada L3":"D",
    "Orificio defectuoso":"D","Esparrago rodado":"C","Esparrago reventado":"D",
    "Caucho roto":"D","fallas de funcionamiento":"D","Falta tuerca":"D",
    "Falta tornillo":"D","Falta abrazadera":"D","Cable reventado":"D",
    "Parte Equivocada":"D","Rosca mala L3":"D","Deterioro":"C",
    "Mal pegada":"C","Mal ubicado":"C","Mal estado":"C","Diferente Medida":"D",
    "Falta calcomanía":"D",
}

PROV_PROCESS = {"SERVIPINTARTE":"batch","INTERAUTOS":"continuo"}

# ============================================================
# MAPEO MODELO → PROVEEDOR (para inferir cuando viene vacío)
# ============================================================
MODELO_PROVEEDOR_MAP = {
    # Royal Enfield
    "CLASSIC 350":"Royal Enfield","CLASSIC 350 GR":"Royal Enfield","GRR 450":"Royal Enfield",
    "HIMALAYAN 452":"Royal Enfield","HNTR 350":"Royal Enfield","INT BEAR 650":"Royal Enfield",
    "METEOR 350":"Royal Enfield","METEOR 350 RE":"Royal Enfield","METEOR 350 STE":"Royal Enfield",
    "METEOR 350 STELLAR":"Royal Enfield","SCRAM 411":"Royal Enfield","SCRAM 411 SPIR":"Royal Enfield",
    "SCRAM 411 SPIRIT":"Royal Enfield",
    # Zonsen
    "AK200ZW":"Zonsen","AK200ZWC":"Zonsen","AK125FLEX EIII":"Zonsen",
    # SYM
    "DYNAMIC RX":"SYM","XC15WX":"SYM","AK125DYN PRO+":"SYM","AK125DYN R+":"SYM","JET EVO":"SYM",
    # Atul
    "ATUL RIK":"Atul",
    # Loncin (todo lo demás con prefijo AK o modelos numéricos típicos)
    "300 RALLY":"Loncin","300AC":"Loncin","300DS":"Loncin","300RALLY":"Loncin","500DSX":"Loncin",
    "AK110NV EIII":"Loncin","AK125CH EIII":"Loncin","AK125CR4 EIII":"Loncin","AK150CR4":"Loncin",
    "AK250CR4 EFI":"Loncin","AK125TTR EIII":"Loncin","AK200TTR EIII":"Loncin","AK125T-4":"Loncin",
    "AK180SR1-ADV":"Loncin","AK200CR3 EIII":"Loncin","AK200CR3 EIII ABS":"Loncin",
    "AK200DS EIII":"Loncin","AK200DS+":"Loncin","AK200DS+ ABS":"Loncin",
    "AK125NKD EIII":"Loncin","DS900X":"Loncin","DS900XÂ ":"Loncin","AK200TT":"Loncin",
    "AK200DS":"Loncin",
}

PROVEEDORES_INTERNACIONALES = {"Royal Enfield","Zonsen","SYM","Atul","Loncin"}

def inferir_proveedor_por_modelo(modelo):
    """Busca coincidencia exacta o parcial del modelo en el mapeo."""
    if not modelo or modelo == "(Sin dato)":
        return None
    modelo_norm = str(modelo).strip()
    if modelo_norm in MODELO_PROVEEDOR_MAP:
        return MODELO_PROVEEDOR_MAP[modelo_norm]
    # Coincidencia parcial (por si vienen con sufijos distintos como EIII, ABS, etc.)
    for key, prov in MODELO_PROVEEDOR_MAP.items():
        key_base = key.split(" EIII")[0].split(" ABS")[0].split(" EFI")[0].strip()
        if modelo_norm.startswith(key_base) and len(key_base) > 2:
            return prov
    return None

def clasificar_tipo_proveedor(proveedor):
    if proveedor in PROVEEDORES_INTERNACIONALES:
        return "Internacional"
    elif proveedor in ["(Sin proveedor)","(Sin dato)"]:
        return "(Sin dato)"
    else:
        return "Nacional"


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
    # Migración: agregar columnas nuevas si la tabla ya existía sin ellas
    cur.execute("PRAGMA table_info(registros)")
    cols_existentes = [row[1] for row in cur.fetchall()]
    if "origen" not in cols_existentes:
        cur.execute("ALTER TABLE registros ADD COLUMN origen TEXT DEFAULT '(Sin dato)'")
    if "tipo_proveedor" not in cols_existentes:
        cur.execute("ALTER TABLE registros ADD COLUMN tipo_proveedor TEXT DEFAULT '(Sin dato)'")
    con.commit(); con.close()

def safe_get(r, *keys, default="(Sin dato)"):
    for k in keys:
        try:
            v = r[k]
            if v is not None and str(v).strip() not in ["","nan","None"]:
                return str(v).strip()
        except: pass
    return default

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
        origen = safe_get(r, "origen", default="(Sin dato)")

        proveedor = safe_get(r,"nombre_proveedor",default="")
        if not proveedor or proveedor in ["(Sin dato)","(Sin proveedor)",""]:
            inferido = inferir_proveedor_por_modelo(modelo)
            proveedor = inferido if inferido else "(Sin proveedor)"

        tipo_prov = clasificar_tipo_proveedor(proveedor)

        rows.append((pid, safe_get(r,"mes",default="(Sin mes)"), proveedor,
            dmg, safe_get(r,"tipo_averia",default="(Sin tipo)"), safe_get(r,"articulo",default="(Sin pieza)"),
            modelo, pnc, pnc*WEIGHTS.get(dmg,2), STD.get(dmg,"C"), origen, tipo_prov))
    cur.executemany("INSERT INTO registros (periodo_id,mes,proveedor,damage,tipo_averia,articulo,modelo,cantidad_pnc,criticidad,std,origen,tipo_proveedor) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
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

def generar_reporte_html(df_scope, titulo, subtitulo, color_key="generic", extra_caption=""):
    """Genera un HTML/PDF descargable a partir de cualquier subconjunto de datos ya filtrado.
    color_key: "servi", "inter", o "generic" para elegir esquema de color.
    """
    import plotly.io as pio, base64

    if df_scope.empty:
        return None

    tot_e  = df_scope["cantidad_pnc"].sum()
    avg_e  = df_scope.groupby("mes")["cantidad_pnc"].sum().mean() if "mes" in df_scope.columns else 0
    pctD_e = df_scope[df_scope["std"]=="D"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
    pctC_e = df_scope[df_scope["std"]=="C"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
    pctT_e = df_scope[df_scope["std"]=="T"]["cantidad_pnc"].sum()/tot_e*100 if tot_e else 0
    top5_def = df_scope.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum")).sort_values("pnc",ascending=False).head(5).reset_index()
    top5_pie = df_scope.groupby("articulo")["cantidad_pnc"].sum().sort_values(ascending=False).head(5).reset_index()

    mes_data = df_scope.groupby("mes")["cantidad_pnc"].sum().reset_index()
    if not mes_data.empty:
        mes_data["_sort"] = mes_data["mes"].apply(sort_mes)
        mes_data = mes_data.sort_values("_sort")
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
    else:
        trend_img = ""

    fig_pie_chart = px.pie(
        values=[df_scope[df_scope["std"]=="D"]["cantidad_pnc"].sum(),
                df_scope[df_scope["std"]=="C"]["cantidad_pnc"].sum(),
                df_scope[df_scope["std"]=="T"]["cantidad_pnc"].sum()],
        names=["Devolución directa","Condicional","Tolerable"],
        color_discrete_map={"Devolución directa":"#c0392b","Condicional":"#c9840a","Tolerable":"#2d6b3f"},
        height=200)
    fig_pie_chart.update_layout(template="plotly_white", margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor="white", font=dict(color="#333"),
        legend=dict(font=dict(size=10)))
    pie_img = base64.b64encode(pio.to_image(fig_pie_chart, format="png", width=320, height=200)).decode()

    fig_def = px.bar(top5_def, x="pnc", y="damage", orientation="h",
        color="std", color_discrete_map=STD_COLORS,
        height=200, labels={"pnc":"PNC","damage":"","std":"STD"})
    fig_def.update_layout(template="plotly_white", margin=dict(l=0,r=10,t=10,b=0),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#333"),
        legend=dict(font=dict(size=10), orientation="h", y=-0.3))
    def_img = base64.b64encode(pio.to_image(fig_def, format="png", width=380, height=200)).decode()

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

    top3_dmg = df_scope.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum"),crit=("criticidad","sum")).sort_values("crit",ascending=False).head(3).reset_index()
    reco_html = ""
    procs_presentes = df_scope["proveedor"].map(PROV_PROCESS).dropna().unique().tolist() if "proveedor" in df_scope.columns else []
    proc_unico = procs_presentes[0] if len(procs_presentes)==1 else None
    for _, r in top3_dmg.iterrows():
        kbE = KB.get(r["damage"], {})
        s = r["std"]
        border = "#c0392b" if s=="D" else "#c9840a" if s=="C" else "#2d6b3f"
        bg = "#fdf0ef" if s=="D" else "#fef9ed" if s=="C" else "#e8f5ec"
        icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
        causa = kbE.get("causas",[""])[0] if kbE.get("causas") else ""
        sol   = kbE.get("soluciones",[""])[0] if kbE.get("soluciones") else ""
        proc_recs = KB.get("_process_recs",{}).get(r["damage"],{})
        proc_rec  = proc_recs.get(proc_unico,"") if proc_unico else ""
        txt = f"{r['pnc']:,.0f} PNC."
        if causa: txt += f" Causa frecuente: {causa}."
        if sol:   txt += f" {sol}."
        if proc_rec: txt += f" {proc_rec}"
        reco_html += f"""<div style="background:{bg};border-left:3px solid {border};
            padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0">
            <div style="font-weight:600;font-size:12px;margin-bottom:3px">{icon} {r['damage']}</div>
            <div style="font-size:11px;color:#444;line-height:1.5">{txt}</div>
        </div>"""
    if not reco_html:
        reco_html = '<p style="font-size:12px;color:#888">Sin datos suficientes para generar recomendaciones.</p>'

    schemes = {
        "servi":   {"dark":"#0f2718","dark2":"#1a3d25","accent":"#3a8a51","light2":"#7dca92"},
        "inter":   {"dark":"#0d1f35","dark2":"#162d4f","accent":"#2d65aa","light2":"#7aaee0"},
        "generic": {"dark":"#1a1a2e","dark2":"#2d2d4a","accent":"#5a5a9a","light2":"#9a9add"},
    }
    cs = schemes.get(color_key, schemes["generic"])

    trend_section = f'''<div class="card page-break-before">
  <div class="card-title">Tendencia mensual de PNC</div>
  <img src="data:image/png;base64,{trend_img}" style="width:100%;border-radius:4px"/>
</div>''' if trend_img else ""

    html_poster = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,*{{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
body{{background:#e8e8e6;font-family:'DM Sans',sans-serif;font-weight:300;padding:28px 40px;color:#111}}
.poster{{max-width:960px;margin:0 auto;display:grid;gap:16px;background:#faf8f3;padding:32px;border-radius:16px;box-shadow:0 4px 32px rgba(0,0,0,.08)}}
.header{{background:{cs["dark"]};border-radius:12px;padding:28px 36px;display:grid;grid-template-columns:1fr auto;align-items:end;gap:20px}}
.hlabel{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:{cs["light2"]};text-transform:uppercase;margin-bottom:6px}}
.htitle{{font-family:'DM Serif Display',serif;font-size:1.9rem;color:#fff;line-height:1.15}}
.hsub{{font-size:12px;color:{cs["light2"]};margin-top:6px}}
.kpis{{display:flex;gap:20px;text-align:right}}
.kpi{{display:flex;flex-direction:column;align-items:flex-end}}
.kval{{font-family:'DM Serif Display',serif;font-size:1.8rem;color:#fff;line-height:1}}
.klbl{{font-size:10px;color:{cs["light2"]};letter-spacing:.08em;text-transform:uppercase;margin-top:3px}}
.kdiv{{width:1px;background:rgba(255,255,255,.15);align-self:stretch}}
.std-band{{background:{cs["dark2"]};border-radius:8px;padding:14px 24px;display:grid;grid-template-columns:auto 1fr 1fr 1fr;align-items:center;gap:0}}
.stdlbl{{font-family:'DM Mono',monospace;font-size:10px;color:{cs["light2"]};text-transform:uppercase;padding-right:20px;border-right:1px solid rgba(255,255,255,.1);white-space:nowrap}}
.std-item{{display:flex;align-items:center;gap:10px;padding:0 16px;border-right:1px solid rgba(255,255,255,.1)}}
.std-item:last-child{{border-right:none}}
.stdnum{{font-family:'DM Serif Display',serif;font-size:1.5rem;color:#fff}}
.stdinf{{display:flex;flex-direction:column}}
.badge{{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-block;margin-bottom:2px}}
.bD{{background:#fde8e8;color:#c0392b}}.bC{{background:#fef3d0;color:#b7760a}}.bT{{background:#e8f5ec;color:#2d6b3f}}
.stdpct{{font-size:11px;color:{cs["light2"]}}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.card{{background:#fff;border-radius:10px;padding:18px 20px;border:1px solid rgba(0,0,0,.06)}}
.card-title{{font-family:'DM Serif Display',serif;font-size:.95rem;color:#0f1520;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #f0ece2}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;font-size:11px;color:#8a9e8e;font-weight:500;padding:0 10px 8px;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #f0ece2}}
.footer{{display:flex;justify-content:space-between;align-items:center;padding:12px 0 0;border-top:1px solid #f0ece2}}
.fbrand{{font-family:'DM Serif Display',serif;font-size:.95rem;color:{cs["accent"]}}}
.fmeta{{font-family:'DM Mono',monospace;font-size:10px;color:#8a9e8e;text-align:right}}
.print-btn{{display:flex;align-items:center;justify-content:center;gap:8px;background:{cs["dark"]};color:#fff;border:none;border-radius:8px;padding:12px 28px;font-family:'DM Sans',sans-serif;font-size:14px;font-weight:500;cursor:pointer;margin:0 auto 20px;transition:opacity .2s;width:fit-content}}
.print-btn:hover{{opacity:.85}}
.card,.std-band,.header{{break-inside:avoid;page-break-inside:avoid}}
.page-break-before{{page-break-before:always;break-before:page}}
@media print{{
  .print-btn{{display:none!important}}
  body{{padding:0;background:#faf8f3!important}}
  .poster{{box-shadow:none!important;border-radius:0!important;padding:10px!important;gap:10px!important}}
  .card,.std-band,.header,.two-col,table,img{{break-inside:avoid;page-break-inside:avoid}}
  .card{{margin-bottom:6px}}
  .page-break-before{{page-break-before:always;break-before:page}}
  @page{{size:A4 portrait;margin:10mm}}
}}
</style></head><body>

<button class="print-btn" onclick="window.print()">
  ⬇️ Descargar como PDF
</button>

<div class="poster">

<header class="header">
  <div>
    <div class="hlabel">Análisis de Calidad — AKT Motos{(' · ' + extra_caption) if extra_caption else ''}</div>
    <h1 class="htitle">{titulo}</h1>
    <p class="hsub">{subtitulo}</p>
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
    <span class="stdnum">{df_scope[df_scope['std']=='D']['cantidad_pnc'].sum():,.0f}</span>
    <div class="stdinf"><span class="badge bD">Devolución directa</span><span class="stdpct">{pctD_e:.0f}% del total</span></div>
  </div>
  <div class="std-item">
    <span class="stdnum">{df_scope[df_scope['std']=='C']['cantidad_pnc'].sum():,.0f}</span>
    <div class="stdinf"><span class="badge bC">Condicional</span><span class="stdpct">{pctC_e:.0f}% del total</span></div>
  </div>
  <div class="std-item">
    <span class="stdnum">{df_scope[df_scope['std']=='T']['cantidad_pnc'].sum():,.0f}</span>
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

{trend_section}

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
    return html_poster


def boton_exportar(df_scope, titulo, subtitulo, color_key="generic", filename_hint="reporte", key_suffix="", extra_caption=""):
    """Muestra un botón de exportar + vista previa para cualquier pestaña."""
    if df_scope is None or df_scope.empty:
        st.caption("No hay datos para exportar con los filtros actuales.")
        return
    with st.expander("📄 Exportar esta vista a PDF"):
        html_rep = generar_reporte_html(df_scope, titulo, subtitulo, color_key, extra_caption)
        if html_rep is None:
            st.caption("No hay datos suficientes para generar el reporte.")
            return
        st.download_button(
            label="⬇️ Descargar (abrir en navegador → Ctrl+P → Guardar como PDF)",
            data=html_rep,
            file_name=f"{filename_hint}.html",
            mime="text/html",
            use_container_width=True,
            type="primary",
            key=f"dl_{key_suffix}"
        )
        st.components.v1.html(html_rep, height=600, scrolling=True)

def generar_reporte_comparativo_html(per_a, per_b, tot_a, tot_b, dev_a, dev_b, pctD_a, pctD_b,
                                      prov_cmp, def_cmp, pie_cmp, insights, filtros_txt=""):
    """Genera un único HTML/PDF con la comparación completa entre dos períodos."""
    import plotly.io as pio, base64

    delta_tot = tot_b - tot_a
    delta_pct = (delta_tot/tot_a*100) if tot_a else 0

    # Gráfica de proveedores
    prov_a2 = prov_cmp[["proveedor", per_a]].rename(columns={per_a:"PNC"}).assign(Período=per_a)
    prov_b2 = prov_cmp[["proveedor", per_b]].rename(columns={per_b:"PNC"}).assign(Período=per_b)
    prov_plot = pd.concat([prov_a2, prov_b2])
    prov_plot["PNC"] = pd.to_numeric(prov_plot["PNC"].astype(str).str.replace(",",""), errors="coerce")
    fig_prov = px.bar(prov_plot, x="proveedor", y="PNC", color="Período", barmode="group",
        height=260, labels={"proveedor":""}, color_discrete_sequence=["#3a8a51","#2d65aa"])
    fig_prov.update_layout(template="plotly_white", margin=dict(l=5,r=5,t=10,b=40),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#333"),
        legend=dict(orientation="h", y=-0.25))
    prov_img = base64.b64encode(pio.to_image(fig_prov, format="png", width=620, height=260)).decode()

    # Tabla proveedores HTML
    prov_rows = ""
    for _, r in prov_cmp.iterrows():
        prov_rows += f"""<tr>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2">{r['proveedor']}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_a]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_b]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right">{r['Tendencia']}</td>
        </tr>"""

    # Tabla defectos top 8
    def_rows = ""
    for _, r in def_cmp.head(8).iterrows():
        def_rows += f"""<tr>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2">{r['Defecto']}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_a]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_b]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right">{r['Tendencia']}</td>
        </tr>"""

    # Tabla piezas top 8
    pie_rows = ""
    for _, r in pie_cmp.head(8).iterrows():
        pie_rows += f"""<tr>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2">{r['Pieza']}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_a]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right;font-family:monospace">{r[per_b]}</td>
          <td style="padding:6px 10px;font-size:11px;border-bottom:1px solid #f0ece2;text-align:right">{r['Tendencia']}</td>
        </tr>"""

    # Insights HTML
    insights_html = ""
    for bg, border, icon, txt in insights:
        insights_html += f"""<div style="background:{bg};border-left:3px solid {border};
            padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0">
            <div style="font-size:11px;color:#333;line-height:1.5">{icon} {txt}</div>
        </div>"""
    if not insights_html:
        insights_html = '<p style="font-size:12px;color:#888">No se detectaron cambios significativos entre los dos períodos.</p>'

    dark, dark2, accent, light2 = "#1a1a2e","#2d2d4a","#5a5a9a","#9a9add"

    html_poster = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,*{{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
body{{background:#e8e8e6;font-family:'DM Sans',sans-serif;font-weight:300;padding:28px 40px;color:#111}}
.poster{{max-width:980px;margin:0 auto;display:grid;gap:16px;background:#faf8f3;padding:32px;border-radius:16px;box-shadow:0 4px 32px rgba(0,0,0,.08)}}
.header{{background:{dark};border-radius:12px;padding:28px 36px}}
.hlabel{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:{light2};text-transform:uppercase;margin-bottom:6px}}
.htitle{{font-family:'DM Serif Display',serif;font-size:1.8rem;color:#fff;line-height:1.2}}
.hsub{{font-size:12px;color:{light2};margin-top:6px}}
.kpis-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}}
.kpi-box{{background:rgba(255,255,255,.06);border-radius:8px;padding:12px 16px}}
.kpi-box-lbl{{font-size:9px;color:{light2};text-transform:uppercase;letter-spacing:.06em}}
.kpi-box-val{{font-family:'DM Serif Display',serif;font-size:1.3rem;color:#fff;margin-top:2px}}
.kpi-box-delta{{font-size:10px;margin-top:2px}}
.card{{background:#fff;border-radius:10px;padding:18px 20px;border:1px solid rgba(0,0,0,.06)}}
.card-title{{font-family:'DM Serif Display',serif;font-size:.95rem;color:#0f1520;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #f0ece2}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;font-size:10px;color:#8a9e8e;font-weight:500;padding:0 10px 8px;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #f0ece2}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.footer{{display:flex;justify-content:space-between;align-items:center;padding:12px 0 0;border-top:1px solid #f0ece2}}
.fbrand{{font-family:'DM Serif Display',serif;font-size:.95rem;color:{accent}}}
.fmeta{{font-family:'DM Mono',monospace;font-size:10px;color:#8a9e8e;text-align:right}}
.print-btn{{display:flex;align-items:center;justify-content:center;gap:8px;background:{dark};color:#fff;border:none;border-radius:8px;padding:12px 28px;font-family:'DM Sans',sans-serif;font-size:14px;font-weight:500;cursor:pointer;margin:0 auto 20px;transition:opacity .2s;width:fit-content}}
.print-btn:hover{{opacity:.85}}
.card,.header{{break-inside:avoid;page-break-inside:avoid}}
.page-break-before{{page-break-before:always;break-before:page}}
@media print{{
  .print-btn{{display:none!important}}
  body{{padding:0;background:#faf8f3!important}}
  .poster{{box-shadow:none!important;border-radius:0!important;padding:10px!important;gap:10px!important}}
  .card,.header,.two-col,table{{break-inside:avoid;page-break-inside:avoid}}
  .card{{margin-bottom:6px}}
  .page-break-before{{page-break-before:always;break-before:page}}
  @page{{size:A4 portrait;margin:10mm}}
}}
</style></head><body>

<button class="print-btn" onclick="window.print()">⬇️ Descargar como PDF</button>

<div class="poster">

<header class="header">
  <div class="hlabel">Comparación de períodos — AKT Motos</div>
  <h1 class="htitle">{per_a} <span style="color:{light2}">vs</span> {per_b}</h1>
  <p class="hsub">{filtros_txt if filtros_txt else "Sin filtros adicionales aplicados"}</p>
  <div class="kpis-row">
    <div class="kpi-box"><div class="kpi-box-lbl">PNC · {per_a}</div><div class="kpi-box-val">{tot_a:,.0f}</div></div>
    <div class="kpi-box"><div class="kpi-box-lbl">PNC · {per_b}</div><div class="kpi-box-val">{tot_b:,.0f}</div>
      <div class="kpi-box-delta" style="color:{'#ff9a8a' if delta_tot>0 else '#9ae8b0'}">{delta_tot:+,.0f} ({delta_pct:+.1f}%)</div></div>
    <div class="kpi-box"><div class="kpi-box-lbl">Dev. directa · {per_a}</div><div class="kpi-box-val">{pctD_a:.0f}%</div></div>
    <div class="kpi-box"><div class="kpi-box-lbl">Dev. directa · {per_b}</div><div class="kpi-box-val">{pctD_b:.0f}%</div></div>
  </div>
</header>

<div class="card">
  <div class="card-title">PNC por proveedor — comparativo</div>
  <img src="data:image/png;base64,{prov_img}" style="width:100%;border-radius:4px"/>
  <table style="margin-top:10px">
    <tr><th>Proveedor</th><th style="text-align:right">{per_a}</th><th style="text-align:right">{per_b}</th><th style="text-align:right">Tendencia</th></tr>
    {prov_rows}
  </table>
</div>

<div class="two-col page-break-before">
  <div class="card">
    <div class="card-title">Top defectos — comparativo</div>
    <table>
      <tr><th>Defecto</th><th style="text-align:right">{per_a}</th><th style="text-align:right">{per_b}</th><th style="text-align:right">Δ</th></tr>
      {def_rows}
    </table>
  </div>
  <div class="card">
    <div class="card-title">Top piezas — comparativo</div>
    <table>
      <tr><th>Pieza</th><th style="text-align:right">{per_a}</th><th style="text-align:right">{per_b}</th><th style="text-align:right">Δ</th></tr>
      {pie_rows}
    </table>
  </div>
</div>

<div class="card">
  <div class="card-title">🔍 Qué cambió — interpretación automática</div>
  {insights_html}
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
    return html_poster


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

    # Filtro de mes — por NOMBRE de mes (sin año), aplica a toda la app
    def extraer_nombre_mes(m):
        m_lower = str(m).lower()
        for n in MES_ORDER:
            if n in m_lower:
                return n.capitalize()
        return str(m)

    _df_preview = get_data(selected_ids)
    if not _df_preview.empty:
        nombres_mes_disponibles = sorted(
            set(extraer_nombre_mes(m) for m in _df_preview["mes"].dropna().unique()),
            key=lambda n: MES_ORDER.index(n.lower()) if n.lower() in MES_ORDER else 99
        )
        meses_sel_nombres = st.multiselect(
            "Filtrar por mes (vacío = todos)",
            nombres_mes_disponibles,
            default=[],
            help="Selecciona por nombre de mes — incluye ese mes de todos los años presentes en los períodos elegidos. Útil para comparar el mismo rango entre años, ej: enero a abril 2025 vs enero a abril 2026"
        )
        if meses_sel_nombres:
            meses_sel = [m for m in _df_preview["mes"].dropna().unique()
                         if extraer_nombre_mes(m) in meses_sel_nombres]
        else:
            meses_sel = []
    else:
        meses_sel = []

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
if meses_sel:
    df = df[df["mes"].isin(meses_sel)]
    if df.empty:
        st.warning("No hay datos para los meses seleccionados"); st.stop()
df["cantidad_pnc"] = pd.to_numeric(df["cantidad_pnc"],errors="coerce").fillna(0)
df["criticidad"]   = pd.to_numeric(df["criticidad"],errors="coerce").fillna(0)
periodo_label = " + ".join(selected)
if meses_sel:
    periodo_label += f" (meses: {', '.join(meses_sel)})"

st.markdown(f'<div class="main-title">🏍 Análisis de Calidad — AKT Motos</div>', unsafe_allow_html=True)
st.markdown(f"**Período:** {periodo_label} · {len(df):,} registros · {df['proveedor'].nunique()} proveedores")
st.markdown("")

tabs = st.tabs(["📊 Resumen","🏭 Por proveedor","🔍 Por defecto","🔧 Por pieza","📈 Comparar períodos","📄 Resúmenes","🗂️ Períodos"])
tab_res, tab_prov, tab_def, tab_pie, tab_comp, tab_export, tab_mgmt = tabs

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

    # Desglose Nacional vs Internacional + filtro por origen
    if "tipo_proveedor" in df.columns:
        st.markdown('<div class="sec-title">Origen del PNC — Nacional vs Internacional</div>', unsafe_allow_html=True)
        tipo_g = df.groupby("tipo_proveedor")["cantidad_pnc"].sum().reset_index()
        tipo_g["pct"] = (tipo_g["cantidad_pnc"]/total*100).round(1) if total else 0

        ti1, ti2 = st.columns(2)
        with ti1:
            fig_tipo = px.pie(tipo_g, values="cantidad_pnc", names="tipo_proveedor", height=260,
                color="tipo_proveedor",
                color_discrete_map={"Nacional":"#3a8a51","Internacional":"#2d65aa","(Sin dato)":"#bbb"})
            fig_tipo.update_layout(margin=dict(l=0,r=0,t=5,b=0), paper_bgcolor="white")
            st.plotly_chart(fig_tipo, use_container_width=True)
        with ti2:
            for _, r in tipo_g.sort_values("cantidad_pnc", ascending=False).iterrows():
                st.metric(r["tipo_proveedor"], f"{r['cantidad_pnc']:,.0f} PNC", f"{r['pct']}% del total")

        with st.expander("🔎 Ver detalle por origen específico (línea, proveedor, etc.)"):
            origenes_disp = sorted(df["origen"].dropna().unique().tolist())
            origen_sel = st.multiselect("Filtrar por origen", origenes_disp, default=[], key="origen_resumen_filter")
            df_origen = df[df["origen"].isin(origen_sel)] if origen_sel else df
            origen_tbl = df_origen.groupby("origen")["cantidad_pnc"].sum().sort_values(ascending=False).reset_index()
            origen_tbl["% del total"] = (origen_tbl["cantidad_pnc"]/total*100).round(1) if total else 0
            origen_tbl.columns = ["Origen","PNC","% del total"]
            origen_tbl["PNC"] = origen_tbl["PNC"].apply(lambda x: f"{x:,.0f}")
            origen_tbl["% del total"] = origen_tbl["% del total"].apply(lambda x: f"{x}%")
            st.dataframe(origen_tbl, use_container_width=True, hide_index=True)

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

    st.divider()
    boton_exportar(df, "Resumen General", f"Período: {periodo_label}",
        color_key="generic", filename_hint=f"Resumen_General_{periodo_label.replace(' ','_')}", key_suffix="resumen")

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

        tipos_en_prov = dfp["tipo_averia"].unique().tolist()
        if not any(t.lower()=="pintura" for t in tipos_en_prov):
            st.caption("ℹ️ La clasificación STD-001 (Devolución/Condicional/Tolerable) es oficial solo para Pintura. Para esta categoría es una aproximación basada en criterio técnico, no un estándar documentado por AKT.")

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

        st.divider()
        cs_prov = "servi" if "SERVI" in prov_sel.upper() else "inter" if "INTER" in prov_sel.upper() else "generic"
        filtros_txt_prov = f"Tipo: {tipo_sel}" if tipo_sel!="Todos" else ""
        boton_exportar(dfp, prov_sel, f"Período: {periodo_label}" + (f" · {filtros_txt_prov}" if filtros_txt_prov else ""),
            color_key=cs_prov, filename_hint=f"Resumen_{prov_sel}_{periodo_label.replace(' ','_')}", key_suffix="proveedor")

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

        st.divider()
        titulo_def = dmg_sel if dmg_sel!="Todos" else "Todos los defectos"
        boton_exportar(dfd, titulo_def, f"Período: {periodo_label}",
            color_key="generic", filename_hint=f"Resumen_Defecto_{titulo_def.replace(' ','_')}", key_suffix="defecto")

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

        st.divider()
        titulo_pie = f"Top piezas — {prov_p}" if prov_p!="Todos" else "Top piezas — Todos los proveedores"
        boton_exportar(dfpi, titulo_pie, f"Período: {periodo_label}",
            color_key="generic", filename_hint=f"Resumen_Piezas_{periodo_label.replace(' ','_')}", key_suffix="pieza")

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
            df_a_full = get_data([id_a])
            df_b_full = get_data([id_b])
            if meses_sel:
                df_a_full = df_a_full[df_a_full["mes"].isin(meses_sel)]
                df_b_full = df_b_full[df_b_full["mes"].isin(meses_sel)]

            if df_a_full.empty or df_b_full.empty:
                st.warning("Uno de los períodos no tiene datos" + (" para los meses seleccionados" if meses_sel else ""))
            else:
                df_a_full["cantidad_pnc"] = pd.to_numeric(df_a_full["cantidad_pnc"],errors="coerce").fillna(0)
                df_b_full["cantidad_pnc"] = pd.to_numeric(df_b_full["cantidad_pnc"],errors="coerce").fillna(0)

                # Filtros — para comparar solo lo que tiene sentido entre archivos de distinto alcance
                st.markdown("##### Filtros de la comparación (opcional)")
                fc1, fc2, fc3 = st.columns(3)

                tipos_disponibles = sorted(set(df_a_full["tipo_averia"].unique()) | set(df_b_full["tipo_averia"].unique()))
                tipo_comp = fc1.multiselect("Tipo de avería", tipos_disponibles, default=[], key="tipo_comp_filter",
                    help="Ej: solo Pintura, cuando un master tiene más categorías que el otro")

                provs_disponibles = sorted(set(df_a_full["proveedor"].unique()) | set(df_b_full["proveedor"].unique()))
                prov_comp = fc2.multiselect("Proveedor", provs_disponibles, default=[], key="prov_comp_filter")

                modelos_disponibles = sorted(set(df_a_full["modelo"].unique()) | set(df_b_full["modelo"].unique()))
                modelo_comp = fc3.multiselect("Modelo", modelos_disponibles, default=[], key="modelo_comp_filter",
                    help="Útil si un período incluye modelos nuevos que el otro no tenía")

                std_comp = st.multiselect("Clasificación STD-001", ["D — Devolución directa","C — Condicional","T — Tolerable"],
                    default=[], key="std_comp_filter")

                df_a, df_b = df_a_full.copy(), df_b_full.copy()
                filtros_activos = []
                if tipo_comp:
                    df_a = df_a[df_a["tipo_averia"].isin(tipo_comp)]
                    df_b = df_b[df_b["tipo_averia"].isin(tipo_comp)]
                    filtros_activos.append(f"Tipo: {', '.join(tipo_comp)}")
                if prov_comp:
                    df_a = df_a[df_a["proveedor"].isin(prov_comp)]
                    df_b = df_b[df_b["proveedor"].isin(prov_comp)]
                    filtros_activos.append(f"Proveedor: {', '.join(prov_comp)}")
                if modelo_comp:
                    df_a = df_a[df_a["modelo"].isin(modelo_comp)]
                    df_b = df_b[df_b["modelo"].isin(modelo_comp)]
                    filtros_activos.append(f"Modelo: {', '.join(modelo_comp)}")
                if std_comp:
                    std_letters = [s[0] for s in std_comp]
                    df_a = df_a[df_a["std"].isin(std_letters)]
                    df_b = df_b[df_b["std"].isin(std_letters)]
                    filtros_activos.append(f"STD-001: {', '.join(std_comp)}")

                if filtros_activos:
                    st.caption("📌 Filtros activos — " + " · ".join(filtros_activos))

                if df_a.empty or df_b.empty:
                    st.warning("No hay datos para esa combinación de filtros en uno de los períodos")
                    st.stop()

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
                def_cmp["Δ_raw"] = def_cmp[per_b] - def_cmp[per_a]
                def_cmp = def_cmp.sort_values(per_b, ascending=False).head(10)

                def_plot = pd.concat([
                    def_cmp[["damage",per_a]].rename(columns={per_a:"PNC"}).assign(Período=per_a),
                    def_cmp[["damage",per_b]].rename(columns={per_b:"PNC"}).assign(Período=per_b)
                ])
                fig_def_cmp = px.bar(def_plot, x="PNC", y="damage", color="Período", orientation="h",
                    barmode="group", height=max(280, len(def_cmp)*32),
                    labels={"damage":""}, color_discrete_sequence=["#3a8a51","#2d65aa"])
                fig_def_cmp.update_layout(margin=dict(l=0,r=0,t=5,b=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(categoryorder="total ascending"))
                st.plotly_chart(fig_def_cmp, use_container_width=True)

                def_cmp["STD"] = def_cmp["damage"].map(STD).map({"D":"🔴","C":"🟡","T":"🟢"}).fillna("⚪")
                def_cmp["Tendencia"] = def_cmp["Δ_raw"].apply(lambda x: "⬆️" if x>0 else "⬇️" if x<0 else "➡️")
                def_cmp["Δ"] = def_cmp["Δ_raw"].apply(lambda x: f"{x:+,.0f}")
                def_cmp[per_a] = def_cmp[per_a].apply(lambda x: f"{x:,.0f}")
                def_cmp[per_b] = def_cmp[per_b].apply(lambda x: f"{x:,.0f}")
                def_cmp_display = def_cmp[["STD","damage",per_a,per_b,"Δ","Tendencia"]].rename(columns={"damage":"Defecto"})
                st.dataframe(def_cmp_display, use_container_width=True, hide_index=True)

                # Top piezas comparativo
                st.markdown('<div class="sec-title">Top piezas críticas — comparativo</div>', unsafe_allow_html=True)
                pie_a = df_a.groupby("articulo")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_a})
                pie_b = df_b.groupby("articulo")["cantidad_pnc"].sum().reset_index().rename(columns={"cantidad_pnc":per_b})
                pie_cmp = pie_a.merge(pie_b, on="articulo", how="outer").fillna(0)
                pie_cmp["Δ_raw"] = pie_cmp[per_b] - pie_cmp[per_a]
                pie_cmp = pie_cmp.sort_values(per_b, ascending=False).head(10)

                pie_plot = pd.concat([
                    pie_cmp[["articulo",per_a]].rename(columns={per_a:"PNC"}).assign(Período=per_a),
                    pie_cmp[["articulo",per_b]].rename(columns={per_b:"PNC"}).assign(Período=per_b)
                ])
                fig_pie_cmp = px.bar(pie_plot, x="PNC", y="articulo", color="Período", orientation="h",
                    barmode="group", height=max(280, len(pie_cmp)*32),
                    labels={"articulo":""}, color_discrete_sequence=["#3a8a51","#2d65aa"])
                fig_pie_cmp.update_layout(margin=dict(l=0,r=0,t=5,b=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(categoryorder="total ascending"))
                st.plotly_chart(fig_pie_cmp, use_container_width=True)

                pie_cmp["Tendencia"] = pie_cmp["Δ_raw"].apply(lambda x: "🔴 Empeoró" if x>0 else "🟢 Mejoró" if x<0 else "➡️ Igual")
                pie_cmp["Δ"] = pie_cmp["Δ_raw"].apply(lambda x: f"{x:+,.0f}")
                pie_cmp[per_a] = pie_cmp[per_a].apply(lambda x: f"{x:,.0f}")
                pie_cmp[per_b] = pie_cmp[per_b].apply(lambda x: f"{x:,.0f}")
                pie_cmp_display = pie_cmp[["articulo",per_a,per_b,"Δ","Tendencia"]].rename(columns={"articulo":"Pieza"})
                st.dataframe(pie_cmp_display, use_container_width=True, hide_index=True)

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


                st.divider()
                with st.expander("📄 Exportar esta comparación a PDF"):
                    st.caption("Genera un único reporte con ambos períodos lado a lado, igual a como se ve en esta pestaña.")
                    html_comp = generar_reporte_comparativo_html(
                        per_a, per_b, tot_a, tot_b, dev_a, dev_b, pctD_a, pctD_b,
                        prov_cmp, def_cmp_display, pie_cmp_display, insights,
                        filtros_txt=" · ".join(filtros_activos) if filtros_activos else ""
                    )
                    st.download_button(
                        "⬇️ Descargar comparación completa",
                        data=html_comp,
                        file_name=f"Comparacion_{per_a.replace(' ','_')}_vs_{per_b.replace(' ','_')}.html",
                        mime="text/html",
                        use_container_width=True,
                        type="primary",
                        key="dl_comp_full"
                    )
                    st.components.v1.html(html_comp, height=700, scrolling=True)

# ── TAB EXPORTAR ─────────────────────────────────────────────
with tab_export:
    st.markdown('<div class="sec-title">Exportar resumen ejecutivo por proveedor</div>', unsafe_allow_html=True)
    st.caption("💡 También puedes exportar lo que estás viendo en cualquier otra pestaña — busca el botón \"📄 Exportar esta vista a PDF\" al final de cada una, con los filtros que tengas aplicados.")

    provs_exp = sorted(df["proveedor"].unique())
    prov_exp = st.selectbox("Proveedor", provs_exp, key="exp_prov")
    df_exp = df[df["proveedor"]==prov_exp].copy()

    if not df_exp.empty:
        is_servi = "SERVI" in prov_exp.upper()
        is_inter = "INTER" in prov_exp.upper()
        color_key = "servi" if is_servi else "inter" if is_inter else "generic"
        prov_title = prov_exp.replace("SERVIPINTARTE","SERVIPINTARTE").replace("INTERAUTOS","INTERAUTOS")
        proc = PROV_PROCESS.get(prov_exp,"")
        proc_lbl = "Por lotes (horno cerrado)" if proc=="batch" else "Línea continua (horno abierto)" if proc=="continuo" else ""
        subtitulo = f"Período: {periodo_label}" + (f" · {proc_lbl}" if proc_lbl else "")

        html_rep = generar_reporte_html(df_exp, prov_title, subtitulo, color_key)
        st.success(f"✅ Resumen listo para {prov_exp}")
        st.download_button(
            label="⬇️ Descargar resumen (abrir en navegador → PDF)",
            data=html_rep,
            file_name=f"Resumen_{prov_exp}_{periodo_label.replace(' ','_')}.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
        st.caption("💡 Al abrir el archivo descargado, usa el botón 'Descargar como PDF' o Ctrl+P → Guardar como PDF")

        with st.expander("👁️ Vista previa del resumen"):
            st.components.v1.html(html_rep, height=800, scrolling=True)

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
