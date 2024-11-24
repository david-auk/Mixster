# Mixster
A open-source spin on the interactive music card game: Hitster

### Setup:

1. Create a .env file


2. Update the .env file:

   ```python
   #Spotify config
   SPOTIFY_CALLBACK_URL='http://127.0.0.1:5050/auth/callback' # Or some other FQDN you configured
   SPOTIFY_CLIENT_ID='<my_spotify_client_id>'
   SPOTIFY_CLIENT_SECRET='<my_spotify_client_secret>'
   
   # MariaDB config
   MYSQL_ROOT_PASSWORD='<my_password>' # Chose any password
   MYSQL_DATABASE_NAME="mixster"
   MYSQL_USER_NAME="mixster_user"
   MYSQL_USER_PASSWORD='<my_password>' # Chose any password
   ```
   
   > Spotify's credentials can be acquired from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

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
        varchar artist_id "NN"
        int release_date "NN"
    }
    
    artist {
        int id PK "NN"
        varchar title "NN"
    }
    
    user {
        int id PK "NN"
        varchar title "NN"
        timestamp last_used "NN"
        timestamp register_date "NN"
    }
    
    %% Relations
    
    user ||--|{ playlist_scan : "scans"
    playlist_scan }|--|| playlist : "updates"
    playlist_scan }|--|{ track : "scapes"
    playlist_scan ||--|| playlist_scan : "extends"
    track }|--|| album : "is_in"
    artist }|--|{ album : "releases"
    
```