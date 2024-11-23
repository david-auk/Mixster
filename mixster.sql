-- Create the `user` table
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    last_used TIMESTAMP NOT NULL,
    register_date TIMESTAMP NOT NULL
);

-- Create the `playlist` table
CREATE TABLE playlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    playlist_image_link VARCHAR(255) NOT NULL
);

-- Create the `playlist_scan` table
CREATE TABLE playlist_scan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    extends_playlist_scan INT,
    playlist_id INT NOT NULL,
    amount_of_tracks INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (extends_playlist_scan) REFERENCES playlist_scan(id) ON DELETE CASCADE,
    FOREIGN KEY (playlist_id) REFERENCES playlist(id) ON DELETE CASCADE
);

-- Create the `artist` table
CREATE TABLE artist (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- Create the `album` table
CREATE TABLE album (
    id INT PRIMARY KEY,
    release_date INT NOT NULL
    -- FOREIGN KEY (artist_id) REFERENCES artist(id) ON DELETE CASCADE
);

-- Create the `track` table
CREATE TABLE track (
    id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    album_id INT NOT NULL,
    FOREIGN KEY (album_id) REFERENCES album(id) ON DELETE CASCADE
);

-- Create the relationship between `playlist_scan` and `track` (many-to-many)
CREATE TABLE playlist_scan_track (
    playlist_scan_id INT NOT NULL,
    track_id INT NOT NULL,
    PRIMARY KEY (playlist_scan_id, track_id),
    FOREIGN KEY (playlist_scan_id) REFERENCES playlist_scan(id) ON DELETE CASCADE,
    FOREIGN KEY (track_id) REFERENCES track(id) ON DELETE CASCADE
);

-- Create the relationship between `user` and `playlist_scan` (one-to-many)
CREATE TABLE user_playlist_scan (
    user_id INT NOT NULL,
    playlist_scan_id INT NOT NULL,
    PRIMARY KEY (user_id, playlist_scan_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (playlist_scan_id) REFERENCES playlist_scan(id) ON DELETE CASCADE
);