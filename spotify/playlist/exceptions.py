class PrivatePlaylistException(Exception):
    def __init__(self, message):
        super().__init__(message)


class PublicPlaylistException(Exception):
    def __init__(self, message):
        super().__init__(message)