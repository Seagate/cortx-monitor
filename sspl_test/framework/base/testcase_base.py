from abc import ABCMeta


class TestCaseBase(metaclass=ABCMeta):

    def init(self):
        raise NotImplementedError()

    def request(self):
        raise NotImplementedError()

    def response(self):
        raise NotImplementedError()

    def filter(self):
        raise NotImplementedError()
