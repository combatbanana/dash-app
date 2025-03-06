import dash
from dash import html
import subprocess
import webbrowser
import os

# Initialize Dash app
app = dash.Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("Design Builder Analysis Tools", style={'textAlign': 'center'}),
    html.P("Choose the tool you want to use:", style={'textAlign': 'center'}),

    html.Div([
        html.Button("Daylighting", id="launch-basic", n_clicks=0),
        html.Button("EnergyPlus", id="launch-advanced", n_clicks=0)
    ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px', 'marginTop': '20px'})
])

# Function to launch the Dash apps
def launch_script(script_name, port):
    """Launch the Dash script on the given port."""
    webbrowser.open(f"http://127.0.0.1:{port}")  # Open in browser

    # Use `start` for Windows to properly launch a new independent process
    subprocess.Popen(f"python {script_name} --port {port}", shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

# Callbacks to launch the selected script
@app.callback(
    dash.Output("launch-basic", "n_clicks"),
    [dash.Input("launch-basic", "n_clicks")]
)
def launch_basic(n_clicks):
    if n_clicks > 0:
        launch_script("dashdaylight.py", 8050)  # Run on port 8050
    return 0  # Reset click count

@app.callback(
    dash.Output("launch-advanced", "n_clicks"),
    [dash.Input("launch-advanced", "n_clicks")]
)
def launch_advanced(n_clicks):
    if n_clicks > 0:
        launch_script("usingdash-moreadvancedwtable.py", 8051)  # Run on port 8051
    return 0  # Reset click count

# Run landing page
if __name__ == "__main__":
    app.run_server(debug=True, port=5000)
