class URLError(Exception):
    def __init__(self, message):
        super().__init__(message)


class PlaylistException(Exception):
    def __init__(self, message):
        super().__init__(message)
