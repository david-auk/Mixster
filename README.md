# Mixster
A open-source spin on the interactive music card game: Hitster

### Setup:

1. Setup [This](#database--datastorage) Database


2. Create a new file: `/spotify/api/secret.py` containing:

    ```python
    SPOTIFY_CLIENT_ID = 'MY_SPOTIFY_CLIENT_ID'
    SPOTIFY_CLIENT_SECRET = 'MY_SPOTIFY_CLIENT_SECRET'
   
    mysql_credenticals = {
        'host': 'MY_HOST', # localhost for most
        'database': 'MY_DATABASE',
        'user': 'MY_DATABASE_USER',
        'password': 'MY_DATABASE_USER_PASSWORD'
   }
   ```
   > Spotify credentials can be acquired from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

   Replacing all strings beginning with `MY_` with your own
   

3. Run flask.py


4. navigate to the flask endpoint (default: http://127.0.0.1:5000/)

### Database / Datastorage:

Almost all information is scraped by the public spotify web interface but to account for playlist change there is also some data storage so a entry can be relinked to a specific scan in time

**ERD**:

```mermaid
erDiagram
    playlist_scan {
        int id PK "NN"
        int extends_playlist_scan FK
        int playlist_id FK "NN"
        int amount_of_tracks "NN"
        timestamp timestamp "NN"
    }

   playlist {
      int id PK "NN"
      varchar title "NN"
      varchar playlist_image_link "NN"
   }
    
    track {
        int id PK "NN"
        varchar title "NN"
        int album_id FK "NN"
        timestamp timestamp "NN"
    }
    
    album {
        int id PK "NN"
        varchar artist "NN"
        int release_date "NN"
    }
    
    user {
        int id PK "NN"
        varchar name "NN"
        timestamp last_used "NN"
        timestamp register_date "NN"
    }
    
    %% Relations
    
    user ||--|{ playlist_scan : "scans"
    playlist_scan }|--|| playlist : "updates"
    playlist_scan }|--|{ track : "scapes"
    playlist_scan ||--|| playlist_scan : "extends"
    track }|--|| album : "gets/puts_info"
    
```