import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import re
from datetime import datetime, date
import time

# Page configuration
st.set_page_config(
    page_title="CSV Massive Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
PRESETS_FILE = "filter_presets.json"
SAMPLE_SIZE_THRESHOLD = 1000000  # If result > this, suggest sampling

# Helper functions for filter presets
def load_presets():
    """Load filter presets from JSON file"""
    try:
        if Path(PRESETS_FILE).exists():
            with open(PRESETS_FILE, 'r', encoding='latin-1') as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Error loading presets: {e}")
        return {}

def save_presets(presets):
    """Save filter presets to JSON file"""
    try:
        with open(PRESETS_FILE, 'w', encoding='latin-1') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving presets: {e}")
        return False

def delete_preset(preset_name):
    """Delete a specific preset"""
    presets = load_presets()
    if preset_name in presets:
        del presets[preset_name]
        save_presets(presets)
        return True
    return False

@st.cache_data
def get_csv_files(folder_path):
    """Get all CSV files from the specified folder"""
    try:
        path = Path(folder_path)
        csv_files = list(path.glob("*.csv"))
        return sorted(csv_files)
    except Exception as e:
        st.error(f"Error reading folder: {e}")
        return []

@st.cache_data
def extract_date_from_filename(filename):
    """Extract date from filename pattern like 'asg-2000-01-31.csv'"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', str(filename))
    if match:
        return match.group(1)
    return None

@st.cache_data
def get_columns_and_sample_data(folder_path):
    """Get column names and sample data from CSV files"""
    try:
        csv_files = get_csv_files(folder_path)
        if not csv_files:
            return None, None
        
        # Read first file to get columns
        first_file = csv_files[0]
        sample_df = pd.read_csv(first_file, nrows=5, encoding='latin-1', sep='|')
        columns = list(sample_df.columns)
        
        return columns, sample_df
    except Exception as e:
        st.error(f"Error reading CSV structure: {e}")
        return None, None

@st.cache_resource
def get_duckdb_connection():
    """Create and return a DuckDB connection with optimized settings"""
    conn = duckdb.connect(database=':memory:')
    # Optimize DuckDB for performance
    conn.execute("SET threads TO 8;")  # Use multiple threads
    conn.execute("SET memory_limit='8GB';")  # Increase memory limit
    conn.execute("SET temp_directory='temp_duckdb';")  # Use temp directory for large operations
    return conn

def get_row_count(conn, folder_path, filters, date_range=None):
    """Get total row count without loading data - FAST"""
    try:
        normalized_path = str(Path(folder_path)).replace('\\', '/')
        
        query = f"""
        SELECT COUNT(*) as total
        FROM read_csv('{normalized_path}/*.csv', 
                      delim='|', 
                      header=true, 
                      union_by_name=true, 
                      encoding='latin-1',
                      auto_detect=false,
                      parallel=true)
        """
        
        where_clauses = []
        
        if date_range and date_range[0] and date_range[1]:
            where_clauses.append(
                f"regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) BETWEEN '{date_range[0]}' AND '{date_range[1]}'"
            )
        
        for col, values in filters.items():
            if values and len(values) > 0:
                escaped_values = [str(v).replace("'", "''") for v in values]
                values_str = "', '".join(escaped_values)
                where_clauses.append(f"{col} IN ('{values_str}')")
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        result = conn.execute(query).fetchone()
        return result[0] if result else 0
    except Exception as e:
        st.error(f"Error counting rows: {e}")
        return 0

def build_query(folder_path, selected_columns, filters, date_range=None, use_sampling=False, sample_size=100000):
    """Build DuckDB query with filters and optional sampling for performance"""
    # Normalize path for Windows
    normalized_path = str(Path(folder_path)).replace('\\', '/')
    
    # Base query with date extraction and robust CSV reading
    query = f"""
    SELECT 
        regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) as fecha,
        {', '.join(selected_columns)}
    FROM read_csv('{normalized_path}/*.csv', 
                  delim='|', 
                  header=true, 
                  filename=true, 
                  union_by_name=true, 
                  encoding='latin-1',
                  ignore_errors=true,
                  auto_detect=false,
                  parallel=true)
    """
    
    where_clauses = []
    
    # Date range filter
    if date_range and date_range[0] and date_range[1]:
        where_clauses.append(
            f"regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) BETWEEN '{date_range[0]}' AND '{date_range[1]}'"
        )
    
    # Column filters
    for col, values in filters.items():
        if values and len(values) > 0:
            # Escape single quotes in values
            escaped_values = [str(v).replace("'", "''") for v in values]
            values_str = "', '".join(escaped_values)
            where_clauses.append(f"{col} IN ('{values_str}')")
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    # Add sampling for large datasets (USING reservoir sampling)
    if use_sampling:
        query += f" USING SAMPLE {sample_size} ROWS"
    
    return query

def execute_query(conn, query, limit=None):
    """Execute query and return results as DataFrame"""
    try:
        if limit:
            query += f" LIMIT {limit}"
        result = conn.execute(query).fetchdf()
        return result
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def main():
    st.title("📊 CSV Massive Data Analyzer")
    st.markdown("Analyze large CSV datasets without loading them entirely into memory")
    
    # Initialize session state
    if 'current_preset' not in st.session_state:
        st.session_state.current_preset = None
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    if 'date_range' not in st.session_state:
        st.session_state.date_range = (None, None)
    if 'cached_results' not in st.session_state:
        st.session_state.cached_results = None
    if 'cached_query' not in st.session_state:
        st.session_state.cached_query = None
    if 'last_config' not in st.session_state:
        st.session_state.last_config = None
    
    # Sidebar - Configuration
    st.sidebar.header("Configuration")
    
    # Folder selector
    folder_path = st.sidebar.text_input(
        "CSV Folder Path",
        value="",
        help="Enter the full path to the folder containing CSV files"
    )
    
    if not folder_path or not Path(folder_path).exists():
        st.info("Please enter a valid folder path in the sidebar to begin")
        st.markdown("""
        ### How to use this tool:
        1. Enter the path to your CSV files folder in the sidebar
        2. Select which columns you want to analyze
        3. Apply filters (optional)
        4. Choose an operation or visualization
        5. Export results if needed
        
        ### Features:
        - Handles datasets up to 90GB+ without loading into memory
        - Automatically extracts dates from filenames
        - Dynamic filters for all columns
        - Save and load filter presets
        - Interactive visualizations
        - Export filtered results
        """)
        return
    
    # Get CSV files and structure
    csv_files = get_csv_files(folder_path)
    if not csv_files:
        st.error("No CSV files found in the specified folder")
        return
    
    st.sidebar.success(f"Found {len(csv_files)} CSV files")
    
    columns, sample_data = get_columns_and_sample_data(folder_path)
    if columns is None:
        st.error("Could not read CSV structure")
        return
    
    # Show sample data
    with st.expander("Data Preview (First file, first 5 rows)", expanded=False):
        st.dataframe(sample_data)
    
    # Presets Management
    st.sidebar.header("Filter Presets")
    presets = load_presets()
    
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        selected_preset = st.selectbox(
            "Load Preset",
            options=[""] + list(presets.keys()),
            key="preset_selector"
        )
    with col2:
        if selected_preset and st.button("🗑️"):
            delete_preset(selected_preset)
            st.rerun()
    
    if selected_preset and selected_preset != st.session_state.current_preset:
        # Load preset
        preset_data = presets[selected_preset]
        st.session_state.filters = preset_data.get('filters', {})
        st.session_state.date_range = tuple(preset_data.get('date_range', (None, None)))
        st.session_state.current_preset = selected_preset
        st.rerun()
    
    # Save new preset
    with st.sidebar.expander("Save Current Filters as Preset"):
        new_preset_name = st.text_input("Preset Name")
        if st.button("Save Preset"):
            if new_preset_name:
                presets[new_preset_name] = {
                    'filters': st.session_state.filters,
                    'date_range': st.session_state.date_range
                }
                if save_presets(presets):
                    st.success(f"Preset '{new_preset_name}' saved!")
                    st.rerun()
            else:
                st.warning("Please enter a preset name")
    
    # Column selector
    st.sidebar.header("Column Selection")
    selected_columns = st.sidebar.multiselect(
        "Select columns to analyze",
        options=columns,
        default=columns[:5] if len(columns) > 5 else columns
    )
    
    if not selected_columns:
        st.warning("Please select at least one column")
        return
    
    # Filters section
    st.sidebar.header("Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.date_range[0] if st.session_state.date_range[0] else None,
            min_value=date(1990, 1, 1),
            max_value=date(2030, 12, 31),
            key="start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.date_range[1] if st.session_state.date_range[1] else None,
            min_value=date(1990, 1, 1),
            max_value=date(2030, 12, 31),
            key="end_date"
        )
    
    date_range = (
        start_date.strftime("%Y-%m-%d") if start_date else None,
        end_date.strftime("%Y-%m-%d") if end_date else None
    )
    st.session_state.date_range = date_range
    
    # Column filters
    st.sidebar.subheader("Column Filters")
    conn = get_duckdb_connection()
    
    filters = {}
    filter_columns = st.sidebar.multiselect(
        "Add filters for columns",
        options=columns,
        help="Select columns you want to filter by"
    )
    
    for col in filter_columns:
        with st.sidebar.expander(f"Filter: {col}"):
            # Manual input for filter values
            filter_input = st.text_input(
                f"Values for {col}",
                value=", ".join(st.session_state.filters.get(col, [])) if col in st.session_state.filters else "",
                key=f"filter_{col}",
                help="Enter values separated by commas (e.g., 1, 2, 3 or A01, A02)"
            )
            
            if filter_input.strip():
                # Split by comma and clean up whitespace
                values = [v.strip() for v in filter_input.split(',') if v.strip()]
                if values:
                    filters[col] = values
                    st.caption(f"Filtering by {len(values)} value(s)")
    
    st.session_state.filters = filters
    
    # Clear filters button
    if st.sidebar.button("Clear All Filters"):
        st.session_state.filters = {}
        st.session_state.date_range = (None, None)
        st.session_state.current_preset = None
        st.session_state.cached_results = None
        st.session_state.last_config = None
        st.rerun()
    
    # Query configuration section
    st.sidebar.markdown("---")
    st.sidebar.header("Query Configuration")
    
    # Row limit for display
    row_limit = st.sidebar.number_input(
        "Max rows to load",
        min_value=100,
        max_value=10000000,
        value=50000,
        step=10000,
        help="Maximum number of rows to load into memory"
    )
    
    # Sampling options
    use_sampling = st.sidebar.checkbox(
        "Use Smart Sampling",
        value=False,
        help="Sample a subset of data for faster visualization. Recommended for large datasets."
    )
    sample_size = 100000
    if use_sampling:
        sample_size = st.sidebar.slider(
            "Sample Size",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000,
            help="Number of rows to sample randomly from the result"
        )
    
    # Create current configuration hash to detect changes
    current_config = {
        'folder': folder_path,
        'columns': tuple(selected_columns),
        'filters': str(sorted(filters.items())),
        'date_range': date_range,
        'use_sampling': use_sampling,
        'sample_size': sample_size if use_sampling else None,
        'row_limit': row_limit
    }
    config_hash = str(current_config)
    
    # Check if configuration changed
    config_changed = (st.session_state.last_config != config_hash)
    
    # Big "Run Query" button
    st.sidebar.markdown("---")
    run_query = st.sidebar.button(
        "RUN QUERY" if config_changed or st.session_state.cached_results is None else "RE-RUN QUERY",
        type="primary",
        use_container_width=True,
        help="Execute query with current filters and settings"
    )
    
    # Show status
    if st.session_state.cached_results is not None and not config_changed:
        st.sidebar.success("Query results loaded")
        st.sidebar.caption(f"Loaded {len(st.session_state.cached_results):,} rows")
    elif config_changed and st.session_state.cached_results is not None:
        st.sidebar.warning("Configuration changed - click RUN QUERY")
    else:
        st.sidebar.info("Click RUN QUERY to load data")
    
    # Execute query if button clicked or if it's the first time
    if run_query or (st.session_state.cached_results is None and not config_changed):
        # Build query
        query = build_query(folder_path, selected_columns, filters, date_range, use_sampling, sample_size)
        
        # Execute query
        start_time = time.time()
        with st.spinner("Loading data..."):
            result_df = execute_query(conn, query, limit=row_limit)
        query_time = time.time() - start_time
        
        # Cache results
        if result_df is not None and not result_df.empty:
            st.session_state.cached_results = result_df
            st.session_state.cached_query = query
            st.session_state.last_config = config_hash
            st.sidebar.success(f"Loaded {len(result_df):,} rows in {query_time:.2f}s")
        else:
            st.session_state.cached_results = None
            st.sidebar.error("No data found")
    
    # Get cached results
    result_df = st.session_state.cached_results
    query = st.session_state.cached_query
    
    # Display quick stats in sidebar
    if result_df is not None:
        st.sidebar.markdown("---")
        st.sidebar.metric("Rows Loaded", f"{len(result_df):,}")
        st.sidebar.metric("Columns", len(result_df.columns))
    
    # Main content area
    tabs = st.tabs(["Data View", "Visualizations", "Operations", "Export"])
    
    # Tab 1: Data View
    with tabs[0]:
        st.header("Data View")
        
        if result_df is None:
            st.info("Configure filters and columns in the sidebar, then click **RUN QUERY** to load data")
            st.markdown("""
            ### Quick Start:
            1. Select the columns you want to analyze
            2. (Optional) Add date range or column filters
            3. Adjust row limit and sampling if needed
            4. Click **RUN QUERY** in the sidebar
            """)
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                if use_sampling:
                    st.info(f"Showing {len(result_df):,} sampled rows")
                else:
                    st.info(f"Loaded {len(result_df):,} rows")
            with col2:
                show_query = st.checkbox("Show SQL Query")
            
            if show_query and query:
                st.code(query, language="sql")
            
            # Display dataframe
            st.dataframe(result_df, use_container_width=True)
            
            # Statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", f"{len(result_df):,}")
            with col2:
                st.metric("Total Columns", len(result_df.columns))
            with col3:
                memory_mb = result_df.memory_usage(deep=True).sum() / 1024 / 1024
                st.metric("Memory Usage", f"{memory_mb:.1f} MB")
    
    # Tab 2: Visualizations
    with tabs[1]:
        st.header("Visualizations")
        
        if result_df is not None and not result_df.empty:
            viz_type = st.selectbox(
                "Select visualization type",
                ["Line Chart", "Bar Chart", "Pie Chart", "Time Series", "Histogram"]
            )
            
            # Get numeric columns
            numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = result_df.select_dtypes(include=['object']).columns.tolist()
            
            if viz_type == "Line Chart":
                col1, col2 = st.columns(2)
                with col1:
                    x_col = st.selectbox("X-axis", options=result_df.columns.tolist(), key="line_x")
                with col2:
                    y_col = st.selectbox("Y-axis", options=numeric_cols, key="line_y")
                
                if x_col and y_col:
                    fig = px.line(result_df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
                    st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Bar Chart":
                col1, col2 = st.columns(2)
                with col1:
                    x_col = st.selectbox("X-axis (Category)", options=categorical_cols, key="bar_x")
                with col2:
                    y_col = st.selectbox("Y-axis (Value)", options=numeric_cols, key="bar_y")
                
                if x_col and y_col:
                    grouped = result_df.groupby(x_col)[y_col].sum().reset_index()
                    fig = px.bar(grouped, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                    st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Pie Chart":
                col1, col2 = st.columns(2)
                with col1:
                    names_col = st.selectbox("Categories", options=categorical_cols, key="pie_names")
                with col2:
                    values_col = st.selectbox("Values", options=numeric_cols, key="pie_values")
                
                if names_col and values_col:
                    grouped = result_df.groupby(names_col)[values_col].sum().reset_index()
                    # Limit to top 10 for readability
                    grouped = grouped.nlargest(10, values_col)
                    fig = px.pie(grouped, names=names_col, values=values_col, 
                               title=f"{values_col} distribution by {names_col} (Top 10)")
                    st.plotly_chart(fig, use_container_width=True)
            
            elif viz_type == "Time Series":
                if 'fecha' in result_df.columns:
                    y_col = st.selectbox("Value column", options=numeric_cols, key="ts_y")
                    if y_col:
                        ts_data = result_df.groupby('fecha')[y_col].sum().reset_index()
                        ts_data['fecha'] = pd.to_datetime(ts_data['fecha'])
                        ts_data = ts_data.sort_values('fecha')
                        fig = px.line(ts_data, x='fecha', y=y_col, 
                                    title=f"{y_col} Time Series")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Date column (fecha) not found in results")
            
            elif viz_type == "Histogram":
                col = st.selectbox("Select column", options=numeric_cols, key="hist_col")
                if col:
                    fig = px.histogram(result_df, x=col, title=f"Distribution of {col}")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for visualization. Please adjust filters.")
    
    # Tab 3: Operations
    with tabs[2]:
        st.header("Operations")
        
        if result_df is None:
            st.info("Load data first by clicking **RUN QUERY** in the sidebar")
            return
        
        st.success("Operations computed on loaded data (fast!)")
        
        # Choice between loaded data or full dataset query
        use_full_dataset = st.checkbox(
            "Query Full Dataset (slower, more accurate for sampled data)",
            value=False,
            help="If you used sampling, enable this to calculate on the complete dataset. Otherwise, calculations use loaded data."
        )
        
        operation = st.selectbox(
            "Select operation",
            ["Summary Statistics", "Count by Column", "Sum", "Average", "Min/Max", "Group By & Aggregate"]
        )
        
        # Get numeric columns
        numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = result_df.select_dtypes(include=['object']).columns.tolist()
        
        if operation == "Summary Statistics":
            st.subheader("Summary Statistics")
            st.info("Statistics computed on loaded data")
            st.dataframe(result_df.describe(), use_container_width=True)
        
        elif operation == "Count by Column":
            st.subheader("Count by Column")
            count_col = st.selectbox("Count by column", options=result_df.columns.tolist())
            top_n = st.slider("Show top N values", min_value=10, max_value=100, value=20, step=5)
            
            if count_col:
                # Use loaded data (instant)
                counts_df = result_df[count_col].value_counts().head(top_n).reset_index()
                counts_df.columns = [count_col, 'count']
                st.dataframe(counts_df, use_container_width=True)
                
                # Optional: show chart
                if len(counts_df) > 0 and len(counts_df) <= 50:
                    fig = px.bar(counts_df, x=count_col, y='count', title=f"Count by {count_col} (Top {top_n})")
                    st.plotly_chart(fig, use_container_width=True)
        
        elif operation == "Sum":
            st.subheader("Sum Aggregation")
            sum_cols = st.multiselect("Select columns to sum", options=numeric_cols)
            if sum_cols:
                sums = result_df[sum_cols].sum()
                sum_df = pd.DataFrame({'Column': sums.index, 'Sum': sums.values})
                st.dataframe(sum_df, use_container_width=True)
        
        elif operation == "Average":
            st.subheader("Average Calculation")
            avg_col = st.selectbox("Select column to average", options=numeric_cols)
            if avg_col:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average", f"{result_df[avg_col].mean():,.2f}")
                with col2:
                    st.metric("Minimum", f"{result_df[avg_col].min():,.2f}")
                with col3:
                    st.metric("Maximum", f"{result_df[avg_col].max():,.2f}")
                with col4:
                    st.metric("Std Dev", f"{result_df[avg_col].std():,.2f}")
        
        elif operation == "Min/Max":
            st.subheader("Minimum and Maximum")
            minmax_col = st.selectbox("Select column", options=numeric_cols)
            if minmax_col:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Minimum", f"{result_df[minmax_col].min():,.2f}")
                with col2:
                    st.metric("Maximum", f"{result_df[minmax_col].max():,.2f}")
                with col3:
                    st.metric("Range", f"{result_df[minmax_col].max() - result_df[minmax_col].min():,.2f}")
        
        elif operation == "Group By & Aggregate":
            st.subheader("Group By Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                group_col = st.selectbox("Group by column", options=result_df.columns.tolist())
            with col2:
                agg_col = st.selectbox("Aggregate column", options=numeric_cols)
            with col3:
                agg_func = st.selectbox("Function", options=["sum", "mean", "count", "min", "max", "std"])
            
            top_n = st.slider("Show top N groups", min_value=10, max_value=200, value=30, step=10)
            
            if group_col and agg_col:
                # Perform aggregation on loaded data (instant)
                if agg_func == "count":
                    grouped_df = result_df.groupby(group_col).size().reset_index(name='count')
                    grouped_df = grouped_df.nlargest(top_n, 'count')
                    agg_col_name = 'count'
                else:
                    grouped_df = result_df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
                    grouped_df.columns = [group_col, f'{agg_func}_{agg_col}']
                    grouped_df = grouped_df.nlargest(top_n, f'{agg_func}_{agg_col}')
                    agg_col_name = f'{agg_func}_{agg_col}'
                
                st.dataframe(grouped_df, use_container_width=True)
                
                # Optional chart
                if len(grouped_df) > 0 and len(grouped_df) <= 50:
                    fig = px.bar(grouped_df, x=group_col, y=agg_col_name,
                               title=f"{agg_func.upper()} of {agg_col} by {group_col} (Top {top_n})")
                    st.plotly_chart(fig, use_container_width=True)
    
    # Tab 4: Export
    with tabs[3]:
        st.header("Export Data")
        
        if result_df is None:
            st.info("Load data first by clicking **RUN QUERY** in the sidebar")
        else:
            st.info("Export the currently loaded data to CSV")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows Loaded", f"{len(result_df):,}")
            with col2:
                st.metric("Columns", len(result_df.columns))
            with col3:
                memory_mb = result_df.memory_usage(deep=True).sum() / 1024 / 1024
                st.metric("Size", f"{memory_mb:.1f} MB")
            
            st.markdown("---")
            
            # Export options
            export_format = st.selectbox("Export format", ["CSV (Latin-1)", "CSV (UTF-8)", "Excel (XLSX)"])
            
            # Generate download button
            if st.button("Generate Download", type="primary", use_container_width=True):
                with st.spinner(f"Generating file with {len(result_df):,} rows..."):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    
                    if "Excel" in export_format:
                        # Export to Excel
                        from io import BytesIO
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='Data')
                        buffer.seek(0)
                        
                        st.download_button(
                            label="⬇Download Excel File",
                            data=buffer,
                            file_name=f"filtered_data_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        # Export to CSV
                        encoding = 'latin-1' if "Latin-1" in export_format else 'utf-8'
                        csv = result_df.to_csv(index=False, encoding=encoding)
                        
                        st.download_button(
                            label="⬇Download CSV",
                            data=csv,
                            file_name=f"filtered_data_{timestamp}.csv",
                            mime="text/csv"
                        )
                    
                    st.success(f"File ready! {len(result_df):,} rows exported")

if __name__ == "__main__":
    main()

