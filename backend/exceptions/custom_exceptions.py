class DataSourceNotFoundException(Exception):
    def __init__(self, message: str):
        self.message = message

class DataSourceEmptyOrCorruptException(Exception):
    def __init__(self, message: str):
        self.message = message

class PageOutOfRangeException(Exception):
    def __init__(self, message: str):
        self.message = message
