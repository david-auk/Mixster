import os


class Config:
    SECRET_KEY = os.urandom(24)
    DEBUG = True
