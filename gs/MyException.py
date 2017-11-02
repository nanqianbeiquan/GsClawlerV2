# coding=utf-8


class StatusCodeException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NotFoundException(Exception):
    def __init__(self, value=u"详情不存在"):
        self.value = value

    def __str__(self):
        return repr(self.value)
