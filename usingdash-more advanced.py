import pandas as pd
import plotly.graph_objects as go
import base64
import io
from dash import Dash, dcc, html, Input, Output, State, ALL, dash_table

app = Dash(__name__)

df = pd.DataFrame()

app.layout = html.Div([
    html.H1("Dynamic Data Band Analyzer"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV File'),
        multiple=False
    ),
    
    dcc.Dropdown(id='parameter-dropdown', placeholder="Select Parameter"),
    dcc.Checklist(id='zone-checklist', inline=True),
    
    html.Div([
        html.Label("Select Date Ranges"),
        html.Button('Add Date Range', id='add-date-range', n_clicks=1),
        html.Div(id='date-range-container', children=[])
    ]),
    
    html.Div([
        html.Label("Select Hour Range"),
        dcc.RangeSlider(
            id='time-slider', min=0, max=23, step=1, value=[0, 23],
            marks={i: str(i) for i in range(0, 24, 2)}
        )
    ]),
    
    html.Div([
        html.Label("Enter Bands (comma separated, e.g. 18,21,30)"),
        dcc.Input(id='bands-input', type='text', value='18,21,30'),
    ]),
    
    html.Div([
        html.Label("Enter Fail Thresholds (format: value:hours, e.g. 25:80,28:40)"),
        dcc.Input(id='fail-thresholds', type='text', value='25:80,28:40'),
    ]),
    
    dcc.Graph(id='data-graph'),
    dash_table.DataTable(id='data-table')
])

@app.callback(
    Output('date-range-container', 'children'),
    Input('add-date-range', 'n_clicks'),
    State('date-range-container', 'children')
)
def add_date_range(n_clicks, children):
    new_date_picker = html.Div([
        dcc.DatePickerRange(
            id={'type': 'date-picker', 'index': n_clicks},
            start_date=None,
            end_date=None,
            display_format='MM-DD'
        )
    ])
    children.append(new_date_picker)
    return children

@app.callback(
    [Output('parameter-dropdown', 'options'),
     Output('zone-checklist', 'options'),
     Output('zone-checklist', 'value')],
    Input('upload-data', 'contents')
)
def parse_data(contents):
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
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.columns = new_columns
        
        # Reformat Datetime manually
        def format_datetime(date_str):
            parts = date_str.split()
            month_day = f"{parts[1]}-{parts[2]}"
            hour = int(parts[4].split(':')[0])
            return month_day, hour
        
        df[['MonthDay', 'Hour']] = df['Datetime'].apply(lambda x: pd.Series(format_datetime(x)))
        
        parameters = set(param_names)
        zones = set(zone_names)
        
        return ([{'label': p, 'value': p} for p in parameters],
                [{'label': z, 'value': z} for z in zones],
                list(zones))
    
    except Exception as e:
        print("Error parsing CSV:", str(e))
        return [], [], []

@app.callback(
    Output('data-graph', 'figure'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input({'type': 'date-picker', 'index': ALL}, 'start_date'),
     Input({'type': 'date-picker', 'index': ALL}, 'end_date'),
     Input('time-slider', 'value'),
     Input('bands-input', 'value')]
)
def update_graph(parameter, selected_zones, start_dates, end_dates, time_range, bands):
    if df.empty or not parameter or not selected_zones:
        print("No data or missing selections.")
        return go.Figure()
    
    date_filters = []
    for start, end in zip(start_dates, end_dates):
        if start and end:
            date_filters.append((df['MonthDay'] >= start) & (df['MonthDay'] <= end))
    
    df_filtered = df[(df['Hour'] >= time_range[0]) & (df['Hour'] <= time_range[1])]
    if date_filters:
        df_filtered = df_filtered[pd.concat(date_filters, axis=1).any(axis=1)]
    
    print("Filtered Data Shape:", df_filtered.shape)
    print(f"Filtered Data for {parameter}:\n", df_filtered[[col for col in df_filtered.columns if parameter in col]].head(10))
    
    bands = [float(x) for x in bands.split(',')]
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

if __name__ == '__main__':
    app.run_server(debug=True)

# Added multiple date range selection 🚀
