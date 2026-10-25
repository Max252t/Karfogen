class CadError(Exception):
    def __init__(self, field, message):
        super(CadError, self).__init__(message)
        self.field = field
        self.message = message

    def __str__(self):
        if self.field:
            return "%s: %s" % (self.field, self.message)
        return self.message
