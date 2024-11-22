-- Create the 'users' table
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    last_used TIMESTAMP NOT NULL,
    register_date TIMESTAMP NOT NULL
);

CREATE TABLE playlist_scan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    extends_playlist_scan INT,
    user_id INT NOT NULL,
    playlist_name VARCHAR(255) NOT NULL,
    playlist_image_link VARCHAR(255) NOT NULL,
    amount_of_tracks INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (extends_playlist_scan) REFERENCES playlist_scan(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE album (
    id INT AUTO_INCREMENT PRIMARY KEY,
    artist VARCHAR(255) NOT NULL,
    release_date INT NOT NULL
);

CREATE TABLE track (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    album_id INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (album_id) REFERENCES album(id) ON DELETE CASCADE
);

CREATE TABLE playlist_scan_track (
    playlist_scan_id INT NOT NULL,
    track_id INT NOT NULL,
    PRIMARY KEY (playlist_scan_id, track_id),
    FOREIGN KEY (playlist_scan_id) REFERENCES playlist_scan(id) ON DELETE CASCADE,
    FOREIGN KEY (track_id) REFERENCES track(id) ON DELETE CASCADE
);