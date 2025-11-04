# CSV Massive Data Analyzer

Una herramienta web para analizar datasets CSV masivos (hasta 90GB+) sin cargar los datos completos en memoria.

## Características

- **Análisis de datasets masivos**: Maneja múltiples archivos CSV grandes sin problemas de memoria
- **Extracción automática de fechas**: Lee la fecha del nombre del archivo y la agrega como columna
- **Filtros dinámicos**: Filtra por fechas, columnas específicas y valores
- **Presets de filtros**: Guarda y carga configuraciones de filtros frecuentes
- **Operaciones matemáticas**: Suma, conteo, promedio, mínimo, máximo, agrupaciones
- **Visualizaciones interactivas**: Gráficos de líneas, barras, pastel, series temporales
- **Exportación**: Descarga los resultados filtrados como CSV

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

2. **Seleccionar columnas**
   - Marca las columnas que quieres analizar
   - Por defecto se muestran las primeras 5 columnas

3. **Aplicar filtros (opcional)**
   - **Filtro por fechas**: Selecciona un rango de fechas
   - **Filtros por columna**: Agrega filtros específicos para cualquier columna
   - **Guardar preset**: Guarda tu configuración de filtros para usarla después

4. **Explorar los datos**
   - **Pestaña "Data View"**: Visualiza los datos filtrados
   - **Pestaña "Visualizations"**: Crea gráficos interactivos
   - **Pestaña "Operations"**: Realiza operaciones matemáticas
   - **Pestaña "Export"**: Exporta los resultados a CSV

### Presets de filtros

Los presets te permiten guardar configuraciones de filtros que uses frecuentemente:

1. Aplica los filtros que desees
2. En la barra lateral, expande "Save Current Filters as Preset"
3. Escribe un nombre para tu preset y haz clic en "Save Preset"
4. Para cargar un preset, selecciónalo del menú desplegable "Load Preset"
5. Para eliminar un preset, selecciónalo y haz clic en el ícono de papelera 🗑️

## Ejemplos de uso

### Análisis básico
1. Selecciona las columnas de interés
2. Ve a la pestaña "Operations"
3. Selecciona "Summary Statistics" para ver estadísticas descriptivas

### Crear visualizaciones
1. Aplica los filtros necesarios
2. Ve a la pestaña "Visualizations"
3. Selecciona el tipo de gráfico que deseas
4. Configura los ejes y columnas

### Exportar datos filtrados
1. Aplica todos los filtros necesarios
2. Ve a la pestaña "Export"
3. Define cuántas filas quieres exportar
4. Haz clic en "Generate CSV for Download"
5. Descarga el archivo CSV

## Tecnologías utilizadas

- **Streamlit**: Interfaz web interactiva
- **DuckDB**: Motor de consultas analíticas que lee CSV sin cargarlos en memoria
- **Pandas**: Manipulación de datos
- **Plotly**: Visualizaciones interactivas

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

### Los filtros no muestran valores
- Esto puede ocurrir si hay demasiados valores únicos (límite de 1000)
- Los valores NULL no se muestran en los filtros

## Notas importantes

- La aplicación no modifica tus archivos CSV originales
- Los datos se leen directamente desde disco, no se cargan completamente en memoria
- La vista de datos está limitada a 10,000 filas por motivos de rendimiento
- Los presets se guardan en `filter_presets.json` en la carpeta de la aplicación

## Soporte

Si encuentras algún problema o tienes preguntas, contacta al desarrollador del proyecto.

## Licencia

Este proyecto fue desarrollado para uso académico.

