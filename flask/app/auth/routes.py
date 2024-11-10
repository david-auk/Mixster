from flask import redirect, request, session
from . import auth_bp
import spotify.api


@auth_bp.route('/authenticate')
def login():
    # Redirect user to Spotify for authorization
    next_url = request.args.get('next', '/')
    login_url = spotify.api.Authenticate.get_login_url()
    return redirect(f"{login_url}&state={next_url}")


@auth_bp.route(f'/{spotify.api.authenticate.SPOTIFY_REDIRECT_URI.split("/")[-1]}')
def callback():

    # Spotify redirects back to your callback with an authorization code
    auth_obj = spotify.api.Authenticate(request.args.get('code'))
    session['access_token'] = auth_obj.get_access_token()

    # Retrieve the 'state' parameter for redirection
    next_url = request.args.get('state', '/')
    return redirect(next_url)


@auth_bp.route('/')
def redirect_to_home():
    return redirect("..")
