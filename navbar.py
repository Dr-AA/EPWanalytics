
# navbar.py
import dash_bootstrap_components as dbc
from dash import html

def create_navbar():
    navbar = html.Div([
        dbc.Row([
            dbc.Col(html.Img(src='assets/logo.jpg', alt='logo', width='150px'), width=2),
            dbc.Col(
                dbc.NavbarSimple(
                    children=[
                        dbc.DropdownMenu(
                            nav=True, in_navbar=True, label="Menu",
                            children=[
                                dbc.DropdownMenuItem("EPW Analytics", href='/epw'),
                                dbc.DropdownMenuItem("Accueil", href='/')
                            ],
                        ),
                    ],
                    brand="WeatherFileAnalytics — Visualisation de données météo",
                    brand_style={"textTransform": "capitalize"},
                    brand_href="/",
                    sticky="top",
                    color="#1f388b",  # couleur de fond
                    dark=True,        # texte clair
                    style={"paddingTop": "10px", "paddingBottom": "25px"}
                )
            )
        ],
        style={"marginBottom": "0px"})
    ])
    return navbar
