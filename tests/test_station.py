from sys import stderr
from traceback import format_exc

class TestStation:
    def __init__(self):
        self.tests = []

    def add_test(self, test_func_name:str):
        self.tests.append(test_func_name)
        self.failed_count = 0

    def run_tests(self):
        for test in self.tests:
            try:
                test()
                print("Test {} OK.".format(test), file=stderr)
            except:
                self.failed_count += 1
                print("Test {} failed. Traceback:".format(test), file=stderr)
                print(format_exc(), file=stderr)
                print(file=stderr)
        if(self.failed_count):
            print("There were {} failed tests. Exiting...".format(self.failed_count), file=stderr)
            exit(1)
        else:
            print("All tests passed!", file=stderr)

if __name__ == "__main__":
    print("It's forbidden to run this file", file=stderr)
    exit(1)
