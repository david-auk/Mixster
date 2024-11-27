-- Create the `user` table
CREATE TABLE user (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    profile_picture_image_url VARCHAR(255) DEFAULT NULL,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    registry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the `playlist` table
CREATE TABLE playlist (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    cover_image_url VARCHAR(255) NOT NULL
);

-- Create the `playlist_scan` table
CREATE TABLE playlist_scan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    extends_playlist_scan INT DEFAULT NULL,
    playlist_id VARCHAR(255) NOT NULL,
    requested_by_user_id VARCHAR(255) NOT NULL,
    amount_of_tracks INT NOT NULL,
    scan_completed BOOLEAN NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extends_playlist_scan) REFERENCES playlist_scan(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (playlist_id) REFERENCES playlist(id) ON DELETE CASCADE
);

-- Create the `artist` table
CREATE TABLE artist (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Create the `album` table
CREATE TABLE album (
    id VARCHAR(255) PRIMARY KEY,
    release_date DATETIME NOT NULL
);

-- Create the relationship between `artist` and `album` (many-to-many)
CREATE TABLE artist_album (
    artist_id VARCHAR(255) NOT NULL,
    album_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (artist_id, album_id),
    FOREIGN KEY (artist_id) REFERENCES artist(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES album(id) ON DELETE CASCADE
);

-- Create the `track` table
CREATE TABLE track (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    album_id VARCHAR(255) NOT NULL,
    FOREIGN KEY (album_id) REFERENCES album(id) ON DELETE CASCADE
);

-- Create the relationship between `playlist_scan` and `track` (many-to-many)
CREATE TABLE playlist_scan_track (
    id INT PRIMARY KEY AUTO_INCREMENT, # As its own column to support the same track id in the same playlist.
    playlist_scan_id INT NOT NULL,
    track_id VARCHAR(255) NOT NULL,
    FOREIGN KEY (playlist_scan_id) REFERENCES playlist_scan(id) ON DELETE CASCADE,
    FOREIGN KEY (track_id) REFERENCES track(id) ON DELETE CASCADE
);