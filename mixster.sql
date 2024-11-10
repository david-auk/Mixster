-- Create the 'users' table
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP
);

-- Create the 'tracks' table
CREATE TABLE tracks (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    requested_by INT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (requested_by) REFERENCES users(id)
);

-- Create the 'scans' table
CREATE TABLE scans (
    id INT PRIMARY KEY,
    playlist_id VARCHAR(255) NOT NULL,
    playlist_name VARCHAR(255),
    playlist_image_link VARCHAR(255),
    requested_by INT,
    created_at TIMESTAMP,
    FOREIGN KEY (requested_by) REFERENCES users(id)
);

-- Create the 'tracks_scans' table
CREATE TABLE tracks_scans (
    id INT PRIMARY KEY,
    track_id VARCHAR(255) NOT NULL,
    scan_id INT NOT NULL,
    FOREIGN KEY (track_id) REFERENCES tracks(id),
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);