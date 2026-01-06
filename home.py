from dash import html

header = html.H4("Bienvenue sur l'interface Data de Energy Management")

contenu = html.H5("Choisissez une application dans le menu")

contenu2 = html.Plaintext("Question ou signalement de bug : a.aurousseau(at)energymgt.ch")

def create_page_home():
    layout = html.Div([
        header,
        contenu,
        contenu2,
    ],style={'marginTop': 10, 'marginBottom': 10, 'marginLeft': 10 , 'marginRight': 10})
    return layout