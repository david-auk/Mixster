# Mixster
A open-source spin on the interactive music card game: Hitster

### Setup:

1. Create a .env file


2. Update the .env file:

   ```python
   # Flask config
   FLASK_PORT=80
   FLASK_HOST="http://127.0.0.1" # Or some other FQDN you configured
   
   #Spotify config
   SPOTIFY_CALLBACK_URL="${FLASK_HOST}:${FLASK_PORT}/auth/callback"
   SPOTIFY_CLIENT_ID='<my_spotify_client_id>'
   SPOTIFY_CLIENT_SECRET='<my_spotify_client_secret>'
   
   # MariaDB config
   MYSQL_ROOT_PASSWORD='<my_password>' # Chose any password
   MYSQL_DATABASE_NAME="mixster"
   MYSQL_USER_NAME="mixster_user"
   MYSQL_USER_PASSWORD='<my_password>' # Chose any password
   
   # Timezone (for data timestamping)
   TIMEZONE="CET"
   ```
   
   > Spotify's credentials can be acquired from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   >
   > Make sure the "SPOTIFY_CALLBACK_URL" is set in the Redirect URIs tab of your dashboard
   
   Replacing all strings beginning with `<my_>` with your own
   

3. Run command `docker compose up -d`


4. navigate to the flask endpoint (default: http://127.0.0.1:5050/)

### Database / Datastorage:

Almost all information is scraped by the public spotify web interface but to account for playlist change there is also some data storage so a entry can be relinked to a specific scan in time

**ERD**:

```mermaid
erDiagram
    playlist_scan {
        int id PK "NN"
        int playlist_id FK "NN"
        varchar requested_by_user_id
        int amount_of_tracks "NN"
        bool export_completed "False"
        int extends_playlist_scan FK
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
    }
    
    album {
        int id PK "NN"
        varchar title "NN"
        int release_date "NN"
    }
    
    artist {
        int id PK "NN"
        varchar name "NN"
    }
    
    user {
        int id PK "NN"
        varchar name "NN"
    }
    
    %% Relations
    
    user ||--|{ playlist_scan : "scans"
    playlist_scan }|--|| playlist : "updates"
    playlist_scan }|--|{ track : "scapes"
    playlist_scan ||--|| playlist_scan : "extends"
    track }|--|| album : "is_in"
    artist }|--|{ track : "releases"
    
```