from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Song
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import spotipy.util as util
import re

def index(request):
    return render(request, 'sonoshareapp/index.html')

def convert_playlist(request):
    if request.method == 'POST':
        playlist_url = request.POST.get('playlist_url')
        if 'youtube.com' in playlist_url or 'youtu.be' in playlist_url:
            return create_user_playlist(request, playlist_url)
        else:
            return render(request, 'sonoshareapp/index.html', {'error': 'Invalid playlist URL'})
    else:
        return redirect('index')

def create_user_playlist(request, playlist_url):
    # Set up Spotify API with authentication using the Authorization Code Flow
    client_id = '31e4302c101d4027ab0da2c6be1763ca'
    client_secret = 'f78a7bde118241c0ae48493ff5bfe4ab'
    redirect_uri = 'http://localhost:3333/callback/'
    scope = 'playlist-modify-public playlist-modify-private'

    # Prompt the user for authorization
    token = util.prompt_for_user_token(request.session.session_key, scope, client_id, client_secret, redirect_uri)

    if token:
        sp = spotipy.Spotify(auth=token)

        # Set up YouTube Music API (unauthenticated)
        ytmusic = YTMusic()

        # Extract the playlist ID from the URL
        playlist_id = extract_playlist_id(playlist_url)

        try:
            playlist_response = ytmusic.get_playlist(playlist_id)
            playlist = playlist_response
        except Exception as e:
            return JsonResponse({'error': f"Error retrieving YouTube Music playlist: {str(e)}"}, status=500)

        # Extract track and artist information from the playlist
        tracks = []
        for item in playlist['tracks']:
            track_name = item['title']
            artist_name = item['artists'][0]['name']
            tracks.append((track_name, artist_name))

        # Create a new playlist on the user's account
        playlist_name = 'My YouTube Music Playlist'
        playlist_description = 'Converted from YouTube Music'
        try:
            spotify_playlist_response = sp.user_playlist_create(user=sp.me()['id'], name=playlist_name, public=True, description=playlist_description)
            spotify_playlist = spotify_playlist_response
        except Exception as e:
            return JsonResponse({'error': f"Error creating Spotify playlist: {str(e)}"}, status=500)

        # Search for each track on Spotify and add it to the playlist
        for track_name, artist_name in tracks:
            query = f'track:{track_name} artist:{artist_name}'
            try:
                search_response = sp.search(q=query, type='track', limit=1)
                results = search_response

                if results['tracks']['items']:
                    track_id = results['tracks']['items'][0]['id']
                    sp.user_playlist_add_tracks(user=sp.me()['id'], playlist_id=spotify_playlist['id'], tracks=[track_id])
            except Exception as e:
                print(f"Error searching for track on Spotify: {track_name} by {artist_name}. Error: {str(e)}")

        playlist_url = spotify_playlist['external_urls']['spotify']
        return render(request, 'sonoshareapp/create_user_playlist.html', {'playlist_url': playlist_url})
    else:
        return redirect('/')

def extract_playlist_id(playlist_url):
    # Extract the playlist ID from the URL using regex
    playlist_id_pattern = re.compile(r'list=([a-zA-Z0-9_-]+)')
    match = playlist_id_pattern.search(playlist_url)

    if match:
        return match.group(1)
    else:
        return None
