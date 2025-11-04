import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import re
from datetime import datetime, date

# Page configuration
st.set_page_config(
    page_title="CSV Massive Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
PRESETS_FILE = "filter_presets.json"

# Helper functions for filter presets
def load_presets():
    """Load filter presets from JSON file"""
    try:
        if Path(PRESETS_FILE).exists():
            with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Error loading presets: {e}")
        return {}

def save_presets(presets):
    """Save filter presets to JSON file"""
    try:
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
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
        sample_df = pd.read_csv(first_file, nrows=5)
        columns = list(sample_df.columns)
        
        return columns, sample_df
    except Exception as e:
        st.error(f"Error reading CSV structure: {e}")
        return None, None

@st.cache_resource
def get_duckdb_connection():
    """Create and return a DuckDB connection"""
    return duckdb.connect(database=':memory:')

def build_query(folder_path, selected_columns, filters, date_range=None):
    """Build DuckDB query with filters"""
    # Base query with date extraction
    query = f"""
    SELECT 
        regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) as fecha,
        {', '.join(selected_columns)}
    FROM read_csv_auto('{folder_path}/*.csv', filename=true, union_by_name=true)
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

def get_unique_values(conn, folder_path, column):
    """Get unique values for a specific column"""
    try:
        query = f"""
        SELECT DISTINCT {column}
        FROM read_csv_auto('{folder_path}/*.csv', union_by_name=true)
        WHERE {column} IS NOT NULL
        ORDER BY {column}
        LIMIT 1000
        """
        result = conn.execute(query).fetchdf()
        return result[column].tolist()
    except Exception as e:
        st.warning(f"Could not get unique values for {column}: {e}")
        return []

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
    
    # Sidebar - Configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Folder selector
    folder_path = st.sidebar.text_input(
        "📁 CSV Folder Path",
        value="",
        help="Enter the full path to the folder containing CSV files"
    )
    
    if not folder_path or not Path(folder_path).exists():
        st.info("👈 Please enter a valid folder path in the sidebar to begin")
        st.markdown("""
        ### How to use this tool:
        1. Enter the path to your CSV files folder in the sidebar
        2. Select which columns you want to analyze
        3. Apply filters (optional)
        4. Choose an operation or visualization
        5. Export results if needed
        
        ### Features:
        - 🚀 Handles datasets up to 90GB+ without loading into memory
        - 📅 Automatically extracts dates from filenames
        - 🔍 Dynamic filters for all columns
        - 💾 Save and load filter presets
        - 📊 Interactive visualizations
        - 📥 Export filtered results
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
    with st.expander("📋 Data Preview (First file, first 5 rows)", expanded=False):
        st.dataframe(sample_data)
    
    # Presets Management
    st.sidebar.header("💾 Filter Presets")
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
    with st.sidebar.expander("💾 Save Current Filters as Preset"):
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
    st.sidebar.header("📊 Column Selection")
    selected_columns = st.sidebar.multiselect(
        "Select columns to analyze",
        options=columns,
        default=columns[:5] if len(columns) > 5 else columns
    )
    
    if not selected_columns:
        st.warning("Please select at least one column")
        return
    
    # Filters section
    st.sidebar.header("🔍 Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.date_range[0],
            key="start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.date_range[1],
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
            unique_vals = get_unique_values(conn, folder_path, col)
            selected_vals = st.multiselect(
                f"Select values for {col}",
                options=unique_vals,
                default=st.session_state.filters.get(col, []),
                key=f"filter_{col}"
            )
            if selected_vals:
                filters[col] = selected_vals
    
    st.session_state.filters = filters
    
    # Clear filters button
    if st.sidebar.button("🔄 Clear All Filters"):
        st.session_state.filters = {}
        st.session_state.date_range = (None, None)
        st.session_state.current_preset = None
        st.rerun()
    
    # Main content area
    tabs = st.tabs(["📊 Data View", "📈 Visualizations", "🔢 Operations", "📥 Export"])
    
    # Build query
    query = build_query(folder_path, selected_columns, filters, date_range)
    
    # Tab 1: Data View
    with tabs[0]:
        st.header("Data View")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Showing filtered data (limited to 10,000 rows for performance)")
        with col2:
            show_query = st.checkbox("Show SQL Query")
        
        if show_query:
            st.code(query, language="sql")
        
        # Execute query with limit
        result_df = execute_query(conn, query, limit=10000)
        
        if result_df is not None and not result_df.empty:
            st.dataframe(result_df, use_container_width=True)
            st.caption(f"Showing {len(result_df)} rows")
        else:
            st.warning("No data found with current filters")
    
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
        
        if result_df is not None and not result_df.empty:
            operation = st.selectbox(
                "Select operation",
                ["Summary Statistics", "Count", "Sum", "Average", "Min/Max", "Group By"]
            )
            
            numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
            
            if operation == "Summary Statistics":
                st.subheader("Summary Statistics")
                st.dataframe(result_df.describe())
            
            elif operation == "Count":
                st.subheader("Row Count")
                st.metric("Total Rows", len(result_df))
                
                # Count by column
                count_col = st.selectbox("Count by column", options=result_df.columns.tolist())
                if count_col:
                    counts = result_df[count_col].value_counts().reset_index()
                    counts.columns = [count_col, 'count']
                    st.dataframe(counts)
            
            elif operation == "Sum":
                st.subheader("Sum")
                sum_cols = st.multiselect("Select columns to sum", options=numeric_cols)
                if sum_cols:
                    sums = result_df[sum_cols].sum()
                    st.dataframe(pd.DataFrame({'Column': sums.index, 'Sum': sums.values}))
            
            elif operation == "Average":
                st.subheader("Average")
                avg_cols = st.multiselect("Select columns to average", options=numeric_cols)
                if avg_cols:
                    avgs = result_df[avg_cols].mean()
                    st.dataframe(pd.DataFrame({'Column': avgs.index, 'Average': avgs.values}))
            
            elif operation == "Min/Max":
                st.subheader("Minimum and Maximum")
                minmax_col = st.selectbox("Select column", options=numeric_cols)
                if minmax_col:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Minimum", result_df[minmax_col].min())
                    with col2:
                        st.metric("Maximum", result_df[minmax_col].max())
            
            elif operation == "Group By":
                st.subheader("Group By Analysis")
                col1, col2, col3 = st.columns(3)
                with col1:
                    group_col = st.selectbox("Group by column", options=result_df.columns.tolist())
                with col2:
                    agg_col = st.selectbox("Aggregate column", options=numeric_cols)
                with col3:
                    agg_func = st.selectbox("Function", options=["sum", "mean", "count", "min", "max"])
                
                if group_col and agg_col and agg_func:
                    grouped = result_df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
                    grouped.columns = [group_col, f'{agg_func}({agg_col})']
                    st.dataframe(grouped)
        else:
            st.info("No data available for operations. Please adjust filters.")
    
    # Tab 4: Export
    with tabs[3]:
        st.header("Export Data")
        
        if result_df is not None and not result_df.empty:
            st.info("Export the filtered dataset to CSV")
            
            col1, col2 = st.columns(2)
            with col1:
                export_limit = st.number_input(
                    "Maximum rows to export",
                    min_value=100,
                    max_value=1000000,
                    value=10000,
                    step=1000
                )
            
            with col2:
                st.metric("Current result size", len(result_df))
            
            if st.button("📥 Generate CSV for Download"):
                # Execute query with specified limit
                export_df = execute_query(conn, query, limit=export_limit)
                
                if export_df is not None:
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name=f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    st.success(f"Ready to download {len(export_df)} rows!")
        else:
            st.info("No data available for export. Please adjust filters.")

if __name__ == "__main__":
    main()

