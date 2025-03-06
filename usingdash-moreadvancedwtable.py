import pandas as pd
import plotly.graph_objects as go
import base64
import io
import dash
from dash import Dash, dcc, html, Input, Output, State, ALL, dash_table
from datetime import datetime

app = Dash(__name__)

df = pd.DataFrame()

app.layout = html.Div([
    html.H1("Design Builder Dynamic Data Band Analyzer"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV File'),
        multiple=False
    ),
    
    dcc.Dropdown(id='parameter-dropdown', placeholder="Select Parameter"),

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
    
    html.Div([
    html.Label("Enter Bands (comma separated, e.g. 18,21,30)"),
    dcc.Input(id='bands-input', type='text', value='18,21,30'),
   html.Button("PMV", id='bands-example-btn-1', n_clicks=0, style={'marginLeft': '10px'}),
    html.Button("DQLS T", id='bands-example-btn-2', n_clicks=0, style={'marginLeft': '5px'}),
    html.Button("DQLS CO2", id='bands-example-btn-3', n_clicks=0, style={'marginLeft': '5px'})
]),
    html.Div([
    html.Label("Enter Fail Thresholds (format: value:hours, e.g. 25:80,28:40)"),
    dcc.Input(id='fail-thresholds', type='text', value='25:80,28:40'),
    html.Button("PMV", id='thresholds-example-btn-1', n_clicks=0, style={'marginLeft': '10px'}),
    html.Button("DQLS T", id='thresholds-example-btn-2', n_clicks=0, style={'marginLeft': '5px'}),
    html.Button("DQLS CO2", id='thresholds-example-btn-3', n_clicks=0, style={'marginLeft': '5px'})
]),
    


    html.Div(id='date-picker-container', children=[]),
    html.Button("Add Date Range", id='add-date-range', n_clicks=0),
    html.Div(id='total-hours-display', style={'fontSize': '18px', 'fontWeight': 'bold', 'marginBottom': '10px'}),
    dcc.RangeSlider(id='time-slider', min=0, max=23, step=1, value=[0, 23],
                    marks={i: str(i) for i in range(0, 24, 2)}),
    html.Label("Select Days of the Week"),
    dcc.RangeSlider(
        id='day-slider',
        min=0,
        max=6,
        step=1,
        value=[0, 6],  # Default to select the whole week
        marks={i: day for i, day in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])}
    ),
    
    
    dcc.Graph(id='data-graph'),
    dash_table.DataTable(
    id='data-table',
    columns=[],  # Columns will be dynamically updated
    data=[],  # Data will be dynamically updated

    editable=False,  # Keep table non-editable
    row_selectable="multi",  # Optional: Allows row selection
    style_table={'overflowX': 'auto'},  # Makes it scrollable
    style_data={'whiteSpace': 'normal', 'height': 'auto'},  # Makes text wrap
),
    html.Button("Copy to Clipboard", id="copy-data-btn", n_clicks=0),
    dcc.Textarea(id="clipboard-data", style={'display': 'none'})
])

@app.callback(
    [Output('parameter-dropdown', 'options'),
     Output('zone-checklist', 'options'),
     Output('zone-checklist', 'value')],
    [Input('upload-data', 'contents'),
     Input('zone-filter', 'value'),
     Input('filter-mode', 'value')]  # <-- Added filter mode toggle
)
def parse_data(contents, filter_word, filter_mode):  # <-- Updated function signature
    global df
    if contents is None:
        return [], [], []
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    csv_data = io.StringIO(decoded.decode('utf-8'))
    
    try:
        df_raw = pd.read_csv(csv_data, skiprows=2, header=None)
        param_names = df_raw.iloc[0, 1:].tolist()
        zone_names = df_raw.iloc[1, 1:].tolist()
        new_columns = ['Datetime'] + [f'{zone} {param}' for zone, param in zip(zone_names, param_names)]
        df = df_raw.iloc[2:].reset_index(drop=True)
        
        df.columns = new_columns
        df.columns = [col.strip() for col in new_columns]  # Remove extra spaces
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['Datetime'] = df['Datetime'].astype(str).str[7:]
        df['Datetime'] = pd.to_datetime(df['Datetime'], format='%b %d %I:%M %p', errors='coerce')
        df = df.dropna(subset=['Datetime'])
        
        df['Date'] = df['Datetime'].dt.date  # Extract the date without time
        
        parameters = set(param_names)
        zones = set(zone_names)

        # **Apply Include/Exclude Filter**
        if filter_word:
            filter_word = filter_word.lower().strip()  # Normalize input
            if filter_mode == 'exclude':
                zones = [z for z in zones if filter_word not in z.lower()]  # Remove matching zones
            elif filter_mode == 'include':
                zones = [z for z in zones if filter_word in z.lower()]  # Keep only matching zones

        return ([{'label': p, 'value': p} for p in parameters],
                [{'label': z, 'value': z} for z in zones],
                list(zones))
    
    except Exception as e:
        print("Error parsing CSV:", str(e))
        return [], [], []

@app.callback(
    Output('date-picker-container', 'children'),
    Input('add-date-range', 'n_clicks'),
    State('date-picker-container', 'children')
)
def add_date_picker(n_clicks, children):
    new_picker = dcc.DatePickerRange(
        id={'type': 'date-picker-range', 'index': n_clicks},
        start_date='1900-01-01',
        end_date=None,
        display_format='YYYY-MM-DD'
    )
    children.append(html.Div(new_picker))
    return children

@app.callback(
    Output('data-graph', 'figure'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input('bands-input', 'value'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'start_date'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'end_date'),
     Input('time-slider', 'value'),
     Input('day-slider', 'value')]  # <-- ADD THIS LINE
)
def update_graph(parameter, selected_zones, bands, start_dates, end_dates, time_range, day_range):
    if df.empty or not parameter or not selected_zones:
        return go.Figure()
    
    df_filtered = df.copy()
    df_filtered['Day_of_Week'] = df_filtered['Datetime'].dt.dayofweek  # Monday = 0, Sunday = 6

    # Apply day filter
    start_day, end_day = day_range
    df_filtered = df_filtered[(df_filtered['Day_of_Week'] >= start_day) &
                              (df_filtered['Day_of_Week'] <= end_day)]

    # Adjust for New Zealand Daylight Savings Time (NZDT)
    # NZDT is from last Sunday in September to first Sunday in April
    def is_daylight_savings(date):
        if date.month < 4 or date.month > 9:  # April - September
            return True  # Daylight savings is active
        return False  # Standard time
    
    # Create a new column for adjusted time
    df_filtered['Adjusted_Hour'] = df_filtered['Datetime'].apply(
        lambda dt: dt.hour - 1 if is_daylight_savings(dt) else dt.hour
    )
    
    # Filter by Date
    if any(start_dates) and any(end_dates):
        filtered_frames = []
        for start_date, end_date in zip(start_dates, end_dates):
            if start_date and end_date:
                mask = (df_filtered['Datetime'].dt.date >= pd.to_datetime(start_date).date()) & \
                       (df_filtered['Datetime'].dt.date <= pd.to_datetime(end_date).date())
                filtered_frames.append(df_filtered[mask])
    
        if filtered_frames:
            df_filtered = pd.concat(filtered_frames)
    
    # Filter by Adjusted Time (instead of normal hour)
    if time_range:
        start_hour, end_hour = time_range
        df_filtered = df_filtered[(df_filtered['Adjusted_Hour'] >= start_hour) & 
                                  (df_filtered['Adjusted_Hour'] <= end_hour)]
    bands = [float(x) for x in bands.split(',') if x.strip()]  # Ignore empty values

    if not bands:  # Prevent empty list errors
        return go.Figure()  # Return an empty figure if no bands are provided
    
    bands.sort()
    band_labels = [f'Below {bands[0]}'] + [f'{bands[i]}-{bands[i+1]}' for i in range(len(bands)-1)] + [f'Above {bands[-1]}']
    
    band_counts = {zone: {label: 0 for label in band_labels} for zone in selected_zones}
    
    for zone in selected_zones:
        col_name = f'{zone} {parameter}'
        if col_name in df_filtered.columns:
            for value in df_filtered[col_name].dropna():
                if value < bands[0]:
                    band_counts[zone][f'Below {bands[0]}'] += 1
                elif value > bands[-1]:
                    band_counts[zone][f'Above {bands[-1]}'] += 1
                else:
                    for i in range(len(bands) - 1):
                        if bands[i] <= value < bands[i + 1]:
                            band_counts[zone][f'{bands[i]}-{bands[i + 1]}'] += 1
    
    fig = go.Figure()
    for band_label in band_labels:
        fig.add_trace(go.Bar(
            x=list(selected_zones),
            y=[band_counts[zone][band_label] for zone in selected_zones],
            name=band_label
        ))
    
    fig.update_layout(
        barmode='stack',
        title=f'{parameter} Distribution Across Zones',
        xaxis_title='Zones',
        yaxis_title='Hours in Band'
    )
    return fig

@app.callback(
    Output('data-table', 'data'),
    Output('data-table', 'columns'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input('bands-input', 'value'),
     Input('fail-thresholds', 'value'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'start_date'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'end_date'),
     Input('time-slider', 'value'),
     Input('day-slider', 'value')]  # <-- ADD THIS LINE
)

def update_table(parameter, selected_zones, bands, fail_thresholds, start_dates, end_dates, time_range, day_range):  # <-- Add time_range here
    
    if df.empty or not parameter or not selected_zones or not fail_thresholds:
        return [], []

    df_filtered = df.copy()
    df_filtered['Day_of_Week'] = df_filtered['Datetime'].dt.dayofweek
    start_day, end_day = day_range
    df_filtered = df_filtered[(df_filtered['Day_of_Week'] >= start_day) &
                              (df_filtered['Day_of_Week'] <= end_day)]
    # Adjust for New Zealand Daylight Savings Time (NZDT)
    # NZDT is from last Sunday in September to first Sunday in April
    def is_daylight_savings(date):
        if date.month < 4 or date.month > 9:  # April - September
            return True  # Daylight savings is active
        return False  # Standard time
    
    # Create a new column for adjusted time
    df_filtered['Adjusted_Hour'] = df_filtered['Datetime'].apply(
        lambda dt: dt.hour - 1 if is_daylight_savings(dt) else dt.hour
    )
    
    # Filter by Date
    if any(start_dates) and any(end_dates):
        filtered_frames = []
        for start_date, end_date in zip(start_dates, end_dates):
            if start_date and end_date:
                mask = (df_filtered['Datetime'].dt.date >= pd.to_datetime(start_date).date()) & \
                       (df_filtered['Datetime'].dt.date <= pd.to_datetime(end_date).date())
                filtered_frames.append(df_filtered[mask])
    
        if filtered_frames:
            df_filtered = pd.concat(filtered_frames)
    
    # Filter by Adjusted Time (instead of normal hour)
    if time_range:
        start_hour, end_hour = time_range
        df_filtered = df_filtered[(df_filtered['Adjusted_Hour'] >= start_hour) & 
                                  (df_filtered['Adjusted_Hour'] <= end_hour)]
    bands = [float(x) for x in bands.split(',') if x.strip()]  # Ignore empty values

    if not bands:
        return [], []  # Prevent further processing if bands is empty
    
    bands.sort()
    band_labels = [f'Below {bands[0]}'] + [f'{bands[i]}-{bands[i+1]}' for i in range(len(bands)-1)] + [f'Above {bands[-1]}']

    # Parse fail thresholds
    fail_checks = []
    try:
        fail_checks = []
        for pair in fail_thresholds.split(','):
            parts = pair.split(':')
            
            if len(parts) == 2:  # Old format (above threshold only, e.g., "25:80")
                value, hours = parts
                fail_checks.append(("above", float(value), int(hours)))  # Assume "above" if no direction is given
            elif len(parts) == 3:  # New format (explicit "above" or "below", e.g., "above:25:80")
                direction, value, hours = parts
                if direction not in ["above", "below"]:
                    print(f"Invalid threshold format: {pair}")  # Debugging: Warn about invalid input
                    continue  # Skip invalid formats
                fail_checks.append((direction, float(value), int(hours)))
            else:
                print(f"Error parsing fail thresholds: {pair}")  # Debugging: Catch unexpected errors
    except Exception as e:
        print("Error parsing fail thresholds:", str(e))
        return [], []

    # Create a DataFrame to store counts
    band_counts = {zone: {label: 0 for label in band_labels} for zone in selected_zones}
    zone_failures = {zone: {} for zone in selected_zones}  # Stores separate statuses per threshold

    print("Available columns in DataFrame:", df_filtered.columns.tolist())  # Debugging: print column names

    for zone in selected_zones:
        matching_cols = [col for col in df_filtered.columns if zone in col and parameter in col]
        
        if not matching_cols:
            print(f"Warning: No match found for zone '{zone}' and parameter '{parameter}' in DataFrame.")
            continue  # Skip this zone if no match found
    
        col_name = matching_cols[0]  # Use the first matching column

        # Assign values to bands
        for value in df_filtered[col_name].dropna():
            if value < bands[0]:
                band_counts[zone][f'Below {bands[0]}'] += 1
            elif value > bands[-1]:
                band_counts[zone][f'Above {bands[-1]}'] += 1
            else:
                for i in range(len(bands) - 1):
                    if bands[i] <= value < bands[i + 1]:
                        band_counts[zone][f'{bands[i]}-{bands[i + 1]}'] += 1

        # Independent Fail Threshold Check
        for direction, threshold, max_hours in fail_checks:
            if col_name not in df_filtered.columns:
                continue  # Skip missing columns safely
            
            if direction == "above":
                hours_above_threshold = df_filtered[col_name].gt(threshold).sum()
                print(f"Zone: {zone} | Hours > {threshold}: {hours_above_threshold} (Limit: {max_hours})")
                zone_failures[zone][f'Fail > {threshold}'] = "Fail" if hours_above_threshold > max_hours else "Pass"
            elif direction == "below":
                hours_below_threshold = df_filtered[col_name].lt(threshold).sum()
                print(f"Zone: {zone} | Hours < {threshold}: {hours_below_threshold} (Limit: {max_hours})")
                zone_failures[zone][f'Fail < {threshold}'] = "Fail" if hours_below_threshold > max_hours else "Pass"

    # Create table data
    table_data = [{'Zone': zone, **counts, **zone_failures[zone]} for zone, counts in band_counts.items()]
    columns = [{'name': 'Zone', 'id': 'Zone'}] + [{'name': band, 'id': band} for band in band_labels] + \
              [{'name': f'Fail {"<" if direction == "below" else ">"} {threshold}','id': f'Fail {"<" if direction == "below" else ">"} {threshold}'} 
               for direction, threshold, _ in fail_checks]
              # Calculate totals for each band column
    totals_row = {'Zone': 'Total'}
    for band in band_labels:
        totals_row[band] = sum(row[band] for row in table_data)
    
    # Leave Fail columns empty or summarize fails
    for direction, threshold, _ in fail_checks:
        fail_col = f'Fail {"<" if direction == "below" else ">"} {threshold}'
        totals_row[fail_col] = ''  # Could summarize total failures if needed
    
    # Append totals row to the data
    table_data.append(totals_row)
    return table_data, columns


@app.callback(
    Output('fail-summary-table', 'data'),
    Output('fail-summary-table', 'columns'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input('fail-thresholds', 'value'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'start_date'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'end_date'),
     Input('time-slider', 'value'),
     Input('day-slider', 'value')]  # <-- ADD THIS LINE
)
def update_fail_summary_table(parameter, selected_zones, fail_thresholds, start_dates, end_dates, time_range, day_range):
    if df.empty or not parameter or not selected_zones or not fail_thresholds:
        return [], []

    df_filtered = df.copy()
    
    df_filtered['Day_of_Week'] = df_filtered['Datetime'].dt.dayofweek
    start_day, end_day = day_range
    df_filtered = df_filtered[(df_filtered['Day_of_Week'] >= start_day) &
                              (df_filtered['Day_of_Week'] <= end_day)]
    
    # Adjust for New Zealand Daylight Savings Time (NZDT)
    def is_daylight_savings(date):
        if date.month < 4 or date.month > 9:
            return True  # Daylight savings is active
        return False  # Standard time
    
    df_filtered['Adjusted_Hour'] = df_filtered['Datetime'].apply(
        lambda dt: dt.hour - 1 if is_daylight_savings(dt) else dt.hour
    )
    
    # Filter by Date
    if any(start_dates) and any(end_dates):
        filtered_frames = []
        for start_date, end_date in zip(start_dates, end_dates):
            if start_date and end_date:
                mask = (df_filtered['Datetime'].dt.date >= pd.to_datetime(start_date).date()) & \
                       (df_filtered['Datetime'].dt.date <= pd.to_datetime(end_date).date())
                filtered_frames.append(df_filtered[mask])
    
        if filtered_frames:
            df_filtered = pd.concat(filtered_frames)
    
    # Filter by Adjusted Time
    start_hour, end_hour = time_range
    df_filtered = df_filtered[(df_filtered['Adjusted_Hour'] >= start_hour) & 
                              (df_filtered['Adjusted_Hour'] <= end_hour)]
    
 
    fail_checks = []
    try:
        for pair in fail_thresholds.split(','):
            parts = [p.strip() for p in pair.split(':')]  # Clean input by removing spaces
    
            if len(parts) == 2:
                value, hours = parts
    
                # Ensure both values are numeric
                if value.replace('.', '', 1).lstrip('-').isdigit() and hours.isdigit():
                    fail_checks.append(("above", float(value), int(hours)))
                else:
                    print(f"Skipping invalid threshold entry: {pair}")  # Debugging
    
            elif len(parts) == 3:
                direction, value, hours = parts
                direction = direction.lower().strip()
    
                # Validate direction and numerical values
                if direction in ["above", "below"] and value.replace('.', '', 1).lstrip('-').isdigit() and hours.isdigit():
                    fail_checks.append((direction, float(value), int(hours)))
                else:
                    print(f"Skipping invalid threshold entry: {pair}")  # Debugging
    
            else:
                print(f"Unexpected format in fail thresholds: {pair}")  # Debugging
    
    except Exception as e:
        print(f"Error parsing fail thresholds: {e}")
        fail_checks = []  # Prevent breaking the app
    


    
    fail_summary = []
    for zone in selected_zones:
        matching_cols = [col for col in df_filtered.columns if zone in col and parameter in col]
        if not matching_cols:
            continue
        
        col_name = matching_cols[0]
        total_hours = len(df_filtered)
        above_fail_hours = 0
        below_fail_hours = 0
        
        for direction, threshold, max_hours in fail_checks:
            if direction == "above":
                above_fail_hours = df_filtered[col_name].gt(threshold).sum()
            elif direction == "below":
                below_fail_hours = df_filtered[col_name].lt(threshold).sum()
        
        total_fail_hours = above_fail_hours + below_fail_hours  # ✅ Add both together

        within_range_hours = total_hours - total_fail_hours
        fail_percentage = (total_fail_hours / total_hours * 100) if total_hours > 0 else 0
        
        fail_summary.append({
    'Zone': zone,
    'Hours Within Range': within_range_hours,
    'Hours Outside Range': total_fail_hours,  # ✅ Uses the corrected total
    'Percentage Outside Range (%)': round((total_fail_hours / total_hours * 100), 2) if total_hours > 0 else 0,
    'Hours Above Threshold': above_fail_hours,  # NEW: Show separate counts
    'Hours Below Threshold': below_fail_hours  # NEW: Show separate counts
})
    
    columns = [
    {'name': 'Zone', 'id': 'Zone'},
    {'name': 'Hours Within Range', 'id': 'Hours Within Range'},
    {'name': 'Hours Outside Range', 'id': 'Hours Outside Range'},
    {'name': 'Hours Above Threshold', 'id': 'Hours Above Threshold'},  # NEW COLUMN
    {'name': 'Hours Below Threshold', 'id': 'Hours Below Threshold'},  # NEW COLUMN
    {'name': 'Percentage Outside Range (%)', 'id': 'Percentage Outside Range (%)'}
]
    
    return fail_summary, columns

app.layout.children.append(
    html.Div([
        dash_table.DataTable(
            id='fail-summary-table',
            columns=[],  # Columns will be dynamically updated
            data=[],  # Data will be dynamically updated

            editable=False,  # Prevents accidental edits
            row_selectable="multi",  # Optional: Lets users select rows
            style_table={'overflowX': 'auto'},  # Enables scrolling
            style_data={'whiteSpace': 'normal', 'height': 'auto'},  # Enables text wrapping
            style_data_conditional=[  # Enables manual text selection
                {
                    'if': {'state': 'selected'},
                    'backgroundColor': 'inherit',  # Keeps normal background when selecting
                    'color': 'inherit',  # Keeps normal text color
                }
            ]
        ),
        html.Button("Copy to Clipboard", id="copy-fail-btn", n_clicks=0),
        dcc.Textarea(id="clipboard-fail", style={'display': 'none'})
        
    ])
)


@app.callback(
    Output('bands-input', 'value'),
    [Input('bands-example-btn-1', 'n_clicks'),
     Input('bands-example-btn-2', 'n_clicks'),
     Input('bands-example-btn-3', 'n_clicks')],
    prevent_initial_call=True
)

def set_bands_example(n1, n2, n3):
    ctx = dash.callback_context  # Get which button was clicked
    if not ctx.triggered:
        return dash.no_update  # Do nothing if no button was clicked

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'bands-example-btn-1':
        return "-1,1"  # Example 1
    elif button_id == 'bands-example-btn-2':
        return "18,19,22,25,30"  # Example 2
    elif button_id == 'bands-example-btn-3':
        return "600,800,1000,2000"  # Example 3

    return dash.no_update
@app.callback(
    Output('fail-thresholds', 'value'),
    [Input('thresholds-example-btn-1', 'n_clicks'),
     Input('thresholds-example-btn-2', 'n_clicks'),
     Input('thresholds-example-btn-3', 'n_clicks')],
    prevent_initial_call=True
)
def set_thresholds_example(n1, n2, n3):
    ctx = dash.callback_context  # Get which button was clicked
    if not ctx.triggered:
        return dash.no_update  # Do nothing if no button was clicked

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'thresholds-example-btn-1':
        return "above:1:20,below:-1:20"  # Example 1
    elif button_id == 'thresholds-example-btn-2':
        return "25:80,28:40"  # Example 2
    elif button_id == 'thresholds-example-btn-3':
        return "800:1,2000:1"  # Example 3

    return dash.no_update


@app.callback(
    Output('average-summary-table', 'data'),
    Output('average-summary-table', 'columns'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input('fail-thresholds', 'value'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'start_date'),
     Input({'type': 'date-picker-range', 'index': ALL}, 'end_date'),
     Input('time-slider', 'value'),
     Input('day-slider', 'value')]
)
def update_average_summary_table(parameter, selected_zones, fail_thresholds, start_dates, end_dates, time_range, day_range):
    if df.empty or not parameter or not selected_zones or not fail_thresholds:
        return [], []

    df_filtered = df.copy()
    df_filtered['Day_of_Week'] = df_filtered['Datetime'].dt.dayofweek
    start_day, end_day = day_range
    df_filtered = df_filtered[(df_filtered['Day_of_Week'] >= start_day) & (df_filtered['Day_of_Week'] <= end_day)]
    
    def is_daylight_savings(date):
        return date.month < 4 or date.month > 9  # NZDT Adjustment

    df_filtered['Adjusted_Hour'] = df_filtered['Datetime'].apply(lambda dt: dt.hour - 1 if is_daylight_savings(dt) else dt.hour)
    
    if any(start_dates) and any(end_dates):
        filtered_frames = []
        for start_date, end_date in zip(start_dates, end_dates):
            if start_date and end_date:
                mask = (df_filtered['Datetime'].dt.date >= pd.to_datetime(start_date).date()) & \
                       (df_filtered['Datetime'].dt.date <= pd.to_datetime(end_date).date())
                filtered_frames.append(df_filtered[mask])
    
        if filtered_frames:
            df_filtered = pd.concat(filtered_frames)
    
    start_hour, end_hour = time_range
    df_filtered = df_filtered[(df_filtered['Adjusted_Hour'] >= start_hour) & (df_filtered['Adjusted_Hour'] <= end_hour)]
    
    fail_checks = []
    peak_threshold = None  # NEW: Only one peak threshold is needed
    
    try:
        for pair in fail_thresholds.split(','):
            parts = [p.strip() for p in pair.split(':')]
            
            if len(parts) == 2 and parts[0].replace('.', '', 1).isdigit() and parts[1] == '1':
                # This is a PEAK threshold (e.g., "2000:1" means no value should exceed 2000)
                peak_threshold = float(parts[0])
    
            elif len(parts) == 2 and parts[0].replace('.', '', 1).isdigit() and parts[1].isdigit():
                # This is an AVERAGE threshold (e.g., "800:1" means average must not exceed 800)
                fail_checks.append(("above_avg", float(parts[0]), int(parts[1])))
    
    except Exception as e:
        print(f"Error parsing fail thresholds: {e}")
        fail_checks = []
        peak_threshold = None


    
    avg_summary = []
    for zone in selected_zones:
        matching_cols = [col for col in df_filtered.columns if zone in col and parameter in col]
        if not matching_cols:
            continue
        
        col_name = matching_cols[0]
        avg_value = df_filtered[col_name].mean(skipna=True)
        max_value = df_filtered[col_name].max(skipna=True)  # Check peak value
        status = "Pass"
        
        # Check against AVERAGE thresholds
        for direction, threshold, _ in fail_checks:
            if direction == "above_avg" and avg_value > threshold:
                status = f"Fail (Avg Exceeds {threshold})"
        
        # Check against PEAK threshold
        if peak_threshold is not None and max_value > peak_threshold:
            if "Fail" in status:
                status += f", Peak Exceeds {peak_threshold}"
            else:
                status = f"Fail (Peak Exceeds {peak_threshold})"

        # Append data with Peak Value
        avg_summary.append({
            'Zone': zone,
            'Average Value': round(avg_value, 2) if not pd.isna(avg_value) else 'N/A',
            'Peak Value': round(max_value, 2) if not pd.isna(max_value) else 'N/A',  # NEW: Add Peak Value Column
            'Status': status
        })

        

        
        avg_summary.append({
            'Zone': zone,
            'Average Value': round(avg_value, 2) if not pd.isna(avg_value) else 'N/A',
            'Status': status
        })
    
    columns = [
        {'name': 'Zone', 'id': 'Zone'},
        {'name': 'Average Value', 'id': 'Average Value'},
        {'name': 'Peak Value', 'id': 'Peak Value'},  # NEW: Add Peak Value Column
        {'name': 'Status', 'id': 'Status'}
    ]
    
    return avg_summary, columns

app.layout.children.append(
    html.Div([
        dash_table.DataTable(
            id='average-summary-table',
            columns=[],
            data=[],

            editable=False,
            row_selectable="multi",
            style_table={'overflowX': 'auto'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'}
        ),
        html.Button("Copy to Clipboard", id="copy-avg-btn", n_clicks=0),
        dcc.Textarea(id="clipboard-avg", style={'display': 'none'})
    ])
)
import pyperclip  # Needed for clipboard functionality

def format_table_for_clipboard(table_data, table_columns):
    """Formats table data into a string suitable for clipboard copying."""
    if not table_data or not table_columns:
        return ""
    
    # Extract column names
    headers = [col["name"] for col in table_columns]
    
    # Convert each row into a comma-separated string
    rows = [",".join(map(str, [row[col["id"]] for col in table_columns])) for row in table_data]

    # Combine headers and rows
    return "\n".join([",".join(headers)] + rows)


@app.callback(
    Output("clipboard-data", "value"),
    Input("copy-data-btn", "n_clicks"),
    State("data-table", "data"),
    State("data-table", "columns"),
    prevent_initial_call=True
)
def copy_data_to_clipboard(n_clicks, table_data, table_columns):
    """Copies the main data table to clipboard."""
    formatted_data = format_table_for_clipboard(table_data, table_columns)
    pyperclip.copy(formatted_data)  # Copy to system clipboard
    return formatted_data


@app.callback(
    Output("clipboard-fail", "value"),
    Input("copy-fail-btn", "n_clicks"),
    State("fail-summary-table", "data"),
    State("fail-summary-table", "columns"),
    prevent_initial_call=True
)
def copy_fail_to_clipboard(n_clicks, table_data, table_columns):
    """Copies the fail summary table to clipboard."""
    formatted_data = format_table_for_clipboard(table_data, table_columns)
    pyperclip.copy(formatted_data)  # Copy to system clipboard
    return formatted_data


@app.callback(
    Output("clipboard-avg", "value"),
    Input("copy-avg-btn", "n_clicks"),
    State("average-summary-table", "data"),
    State("average-summary-table", "columns"),
    prevent_initial_call=True
)
def copy_avg_to_clipboard(n_clicks, table_data, table_columns):
    """Copies the average summary table to clipboard."""
    formatted_data = format_table_for_clipboard(table_data, table_columns)
    pyperclip.copy(formatted_data)  # Copy to system clipboard
    return formatted_data

import sys

# Default port
port = 8051  # Fallback if no argument is provided

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