# CSV Massive Data Analyzer

Una herramienta web para analizar datasets CSV masivos (hasta 90GB+) sin cargar los datos completos en memoria.

## Características

- **Análisis de datasets masivos**: Maneja múltiples archivos CSV grandes sin problemas de memoria
- **Motor optimizado**: DuckDB con procesamiento paralelo, 8 threads y 4GB de memoria
- **Conteo rápido**: Cuenta millones de filas en segundos sin cargar datos
- **Smart Sampling**: Muestreo inteligente para datasets grandes (visualización instantánea)
- **Extracción automática de fechas**: Lee la fecha del nombre del archivo y la agrega como columna
- **Filtros dinámicos**: Filtra por fechas, columnas específicas y valores
- **Presets de filtros**: Guarda y carga configuraciones de filtros frecuentes
- **Operaciones optimizadas**: Todas las agregaciones se hacen en DuckDB (sin cargar datos en memoria)
  - Suma, conteo, promedio, mínimo, máximo calculados sobre el dataset completo
  - Agrupaciones con visualizaciones automáticas
- **Visualizaciones interactivas**: Gráficos de líneas, barras, pastel, series temporales
- **Exportación flexible**: Descarga hasta 10 millones de filas filtradas

## Requisitos

- **Python 3.8 o superior**
- Windows (los scripts de instalación están diseñados para Windows)
- Conexión a internet (solo para instalación)

## Instalación

### Paso 1: Verificar Python

Abre PowerShell o Command Prompt y verifica que Python esté instalado:

```bash
python --version
```

Si no tienes Python instalado, descárgalo desde: https://www.python.org/downloads/

**Importante**: Durante la instalación de Python, marca la opción "Add Python to PATH"

### Paso 2: Instalar la aplicación

1. Descarga o clona este proyecto en tu computadora
2. Abre la carpeta del proyecto en el explorador de archivos
3. Haz doble clic en `instalar.bat`
4. Espera a que termine la instalación (puede tomar unos minutos)

## Uso

### Iniciar la aplicación

1. Haz doble clic en `ejecutar.bat`
2. La aplicación se abrirá automáticamente en tu navegador
3. Para detener la aplicación, presiona `Ctrl+C` en la ventana de comandos

### Usar la interfaz

1. **Seleccionar carpeta de datos**
   - En la barra lateral, ingresa la ruta completa a la carpeta que contiene tus archivos CSV
   - Ejemplo: `C:\Users\TuUsuario\Documents\datos_csv`

2. **(Opcional) Excluir archivos problemáticos**
   - Si algún archivo da error, expande "Exclude Problematic Files"
   - Haz clic en "Auto-Detect" para detectar automáticamente archivos con problemas
   - O escribe manualmente los nombres de archivos a excluir (uno por línea)
   - Haz clic en "Apply"

3. **Seleccionar columnas**
   - Marca las columnas que quieres analizar
   - Por defecto se muestran las primeras 5 columnas

4. **Aplicar filtros (opcional)**
   - **Filtro por fechas**: 
     - Activa el checkbox "Enable date filter"
     - Selecciona el rango de fechas deseado
     - Desactiva el checkbox para quitar el filtro
   - **Filtros por columna**: 
     - Selecciona las columnas que quieres filtrar
     - Escribe los valores manualmente, separados por comas
     - Ejemplo: `1, 2, 3` o `A01, A02, A03`
   - **Guardar preset**: Guarda tu configuración de filtros para usarla después

5. **Configurar la query**
   - **Max rows to load**: Define cuántas filas cargar (por defecto 50,000)
   - **Smart Sampling**: Activa para datasets grandes - carga una muestra representativa
   - **Importante**: Puedes cambiar columnas y filtros SIN ejecutar la query todavía

6. **Ejecutar la query**
   - Haz clic en el botón **RUN QUERY** en la barra lateral
   - Los datos se cargan UNA SOLA VEZ y se cachean en memoria
   - El botón muestra advertencia si cambias la configuración (necesitas re-ejecutar)

7. **Explorar los datos cacheados (RÁPIDO - sin queries adicionales)**
   - **Pestaña "Data View"**: Visualiza los datos cargados
   - **Pestaña "Visualizations"**: Crea gráficos interactivos
   - **Pestaña "Operations"**: Realiza operaciones matemáticas instantáneas
   - **Pestaña "Export"**: Exporta los datos cargados a CSV o Excel

### Presets de filtros

Los presets te permiten guardar configuraciones de filtros que uses frecuentemente:

1. Aplica los filtros que desees
2. En la barra lateral, expande "Save Current Filters as Preset"
3. Escribe un nombre para tu preset y haz clic en "Save Preset"
4. Para cargar un preset, selecciónalo del menú desplegable "Load Preset"
5. Para eliminar un preset, selecciónalo y haz clic en el ícono de papelera 🗑️

## Solución de problemas

### "Python is not installed or not in PATH"
- Asegúrate de tener Python instalado
- Durante la instalación de Python, marca "Add Python to PATH"
- Reinicia tu computadora después de instalar Python

### "Virtual environment not found"
- Ejecuta `instalar.bat` primero antes de usar `ejecutar.bat`

### La aplicación no se abre en el navegador
- Espera unos segundos después de ejecutar `ejecutar.bat`
- Si no se abre automáticamente, copia la URL que aparece en la consola (generalmente `http://localhost:8501`)
- Pégala en tu navegador

### Errores al leer los archivos CSV
- Verifica que la ruta a la carpeta sea correcta
- Asegúrate de que los archivos tengan extensión `.csv`
- Verifica que tengas permisos de lectura en la carpeta

### Error "Error when sniffing file" o archivos corruptos
- **Síntoma**: Aparece error al intentar cargar datos con un archivo específico
- **Solución**: Usa la sección "Exclude Problematic Files" en el sidebar
  1. Expande la sección "Exclude Problematic Files"
  2. Escribe el nombre del archivo problemático (ej: `asg-2005-01-31.csv`)
  3. Haz clic en "Apply Exclusions"
  4. Intenta ejecutar la query nuevamente
- La aplicación seguirá funcionando con el resto de archivos

### Los filtros no funcionan
- Verifica que los valores estén escritos correctamente
- Asegúrate de usar comas para separar múltiples valores
- Los valores son case-sensitive (distinguen mayúsculas/minúsculas)

## Optimizaciones de Rendimiento

Esta herramienta está altamente optimizada para manejar millones de filas:

## Notas importantes

- La aplicación no modifica tus archivos CSV originales
- Los datos se leen directamente desde disco, no se cargan completamente en memoria
- La vista de datos tiene un límite configurable (por defecto 50,000 filas) para evitar problemas de memoria en el navegador
- El límite de tamaño de mensaje se ha configurado a 4 GB para manejar datasets grandes
- Los presets se guardan en `filter_presets.json` en la carpeta de la aplicación
- DuckDB usa `temp_duckdb/` para operaciones temporales en disco
- **Rendimiento esperado**: 
  - Contar 10 millones de filas: 2-5 segundos
  - Sumar/Promediar 10 millones: 3-8 segundos
  - Agrupar y agregar: 5-15 segundos (dependiendo de cardinalidad)

## Soporte

Si encuentras algún problema o tienes preguntas, contacta al desarrollador del proyecto (o a Diegus).

## Licencia

Este proyecto fue desarrollado para uso académico.

