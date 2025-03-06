import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import base64
import io
import pyperclip  # For copying data to clipboard

# Initialize the Dash app
app = dash.Dash(__name__)

df = pd.DataFrame()  # Placeholder for uploaded data

app.layout = html.Div([
    html.H1("Daylighting Analysis"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV File'),
        multiple=False
    ),
    
    html.Label("Set UDI Threshold (%):"),
    dcc.Input(id='udi-threshold', type='number', value=50, min=0, max=100),
    
    html.Label("Set sDA Threshold (%):"),
    dcc.Input(id='sda-threshold', type='number', value=50, min=0, max=100),
    
    html.Label("Filter Zones (Include or Exclude containing word):"),
    dcc.Input(id='zone-filter', type='text', placeholder='Enter word to filter'),
    dcc.RadioItems(
        id='filter-mode',
        options=[
            {'label': 'Exclude', 'value': 'exclude'},
            {'label': 'Include', 'value': 'include'}
        ],
        value='exclude',  # Default to 'exclude'
        inline=True
    ),
    dcc.Checklist(id='zone-checklist', inline=False),
    
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        style_table={'overflowX': 'auto'}
    ),
    
    html.Button("Copy Table to Clipboard", id="copy-btn", n_clicks=0),
    html.H3("Summary Table"),
    dash_table.DataTable(
        id='summary-table',
        columns=[
            {'name': 'Metric', 'id': 'Metric'},
            {'name': 'Percentage (%)', 'id': 'Percentage'}
        ],
        data=[],
        style_table={'overflowX': 'auto'}
    ),

    dcc.Textarea(id="clipboard-data", style={'display': 'none'})
    
])

@app.callback(
    [Output('data-table', 'data'),
     Output('data-table', 'columns'),
     Output('zone-checklist', 'options'),
     Output('summary-table', 'data')],  # Add this output
    [Input('upload-data', 'contents'),
     Input('udi-threshold', 'value'),
     Input('sda-threshold', 'value'),
     Input('zone-filter', 'value'),
     Input('filter-mode', 'value'),
     Input('zone-checklist', 'value')]
)

def parse_and_update_data(contents, udi_threshold, sda_threshold, zone_filter, filter_mode, selected_zones):
    global df
    if contents:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        csv_data = io.StringIO(decoded.decode('utf-8'))
        
        try:
            df = pd.read_csv(csv_data)
        except Exception as e:
            print("Error parsing CSV:", str(e))
            return [], [], []

    if df.empty:
        return [], [], [], []  # Ensure four outputs


    # Generate checklist options from full dataset (not filtered)
    all_zones = df['Zone'].dropna().unique().tolist()
    checklist_options = [{'label': z, 'value': z} for z in all_zones]

    # Apply filtering by selected zones
    filtered_df = df.copy()
    if selected_zones:
        filtered_df = filtered_df[filtered_df['Zone'].isin(selected_zones)]
    
    # Apply text-based filtering
    if zone_filter:
        if filter_mode == 'exclude':
            filtered_df = filtered_df[~filtered_df['Zone'].str.contains(zone_filter, case=False, na=False)]
        else:
            filtered_df = filtered_df[filtered_df['Zone'].str.contains(zone_filter, case=False, na=False)]
    
    # Apply pass/fail conditions
    filtered_df['sDA Pass/Fail'] = filtered_df['sDA Area in Range (%)'].apply(lambda x: 'Pass' if x >= sda_threshold else 'Fail')
    filtered_df['UDI Pass/Fail'] = filtered_df['UDI Area in Range (%)'].apply(lambda x: 'Pass' if x >= udi_threshold else 'Fail')
    

    numeric_cols = filtered_df.select_dtypes(include=['number']).columns
    total_row = {col: filtered_df[col].sum() for col in numeric_cols}
    
    # Add Zone Label for the total row
    total_row['Zone'] = 'TOTAL'
    if 'Total Area' in filtered_df.columns:
        total_row['Total Area'] = filtered_df['Total Area'].sum()

# Append total row using pd.concat()
    filtered_df = pd.concat([filtered_df, pd.DataFrame([total_row])], ignore_index=True)
# Extract total values from the appended "TOTAL" row
    # Extract total values safely
    
    
    total_area = total_row.get('Floor Area (m2)', 0) or total_row.get('Total Area (m²)', 0)
    print(total_area)
    total_sda_area = total_row.get('sDA Area in Range (m2)', 0)
    total_udi_area = total_row.get('UDI Area in Range (m2)', 0)
    total_ase_area = total_row.get('ASE Area in Range (m2)', 0)
    
    # Compute correct percentages
    sda_percentage = (total_sda_area / total_area) * 100 if total_area > 0 else 0
    udi_percentage = (total_udi_area / total_area) * 100 if total_area > 0 else 0
    ase_percentage = (total_ase_area / total_area) * 100 if total_area > 0 else 0
    
    # Create summary table data
    summary_data = [
        {'Metric': 'sDA%', 'Percentage': round(sda_percentage, 2)},
        {'Metric': 'UDI%', 'Percentage': round(udi_percentage, 2)},
        {'Metric': 'ASE%', 'Percentage': round(ase_percentage, 2)}
    ]


    
    return (filtered_df.to_dict('records'),
        [{'name': i, 'id': i} for i in filtered_df.columns],
        checklist_options,
        summary_data)

@app.callback(
    Output("clipboard-data", "value"),
    Input("copy-btn", "n_clicks"),
    State("data-table", "data"),
    State("data-table", "columns"),
    prevent_initial_call=True
)
def copy_table_to_clipboard(n_clicks, table_data, table_columns):
    if not table_data or not table_columns:
        return ""
    
    headers = [col["name"] for col in table_columns]
    rows = ["\t".join(map(str, [row[col["id"]] for col in table_columns])) for row in table_data]
    clipboard_text = "\n".join(["\t".join(headers)] + rows)
    pyperclip.copy(clipboard_text)
    return clipboard_text

import sys

# Default port
port = 8050  # Fallback if no argument is provided

# Check if "--port" argument is passed in the command line
for i in range(len(sys.argv)):
    if sys.argv[i] == "--port" and i + 1 < len(sys.argv):
        try:
            port = int(sys.argv[i + 1])  # Convert argument to an integer
        except ValueError:
            print("Invalid port argument. Using default port 8050.")

# Run the app on the specified port
if __name__ == '__main__':
    app.run_server(debug=False, port=port)