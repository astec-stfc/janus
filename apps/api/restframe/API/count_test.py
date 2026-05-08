import timeit
from typing import Union, List


def count_trues1(true_list: list):
    true_list = list(true_list) if not isinstance(true_list, list) else true_list
    i = 0
    while i < len(true_list) and true_list[i]:
        i += 1
    return i


def count_trues2(true_list: list):
    true_list = list(true_list) if not isinstance(true_list, list) else true_list
    for i, x in enumerate(true_list):
        if not x:
            return i
    return len(true_list)


def count_trues3(true_list: list):
    true_list = list(true_list) if not isinstance(true_list, list) else true_list
    try:
        return true_list.index(False)
    except ValueError:
        return len(true_list)


test_list = (
    [True, True] + [True] * int(10000) + [True, True, True, False, True, True, True]
)
# test_list = [True]*100000
for f in [count_trues1, count_trues2, count_trues3]:
    print(f.__name__, f(test_list))

n = 10
result = timeit.timeit(stmt="count_trues1(test_list)", globals=globals(), number=n)
print(f"Execution time is {result / n * 1e6} µs")
result = timeit.timeit(stmt="count_trues2(test_list)", globals=globals(), number=n)
print(f"Execution time is {result / n * 1e6} µs")
result = timeit.timeit(stmt="count_trues3(test_list)", globals=globals(), number=n)
print(f"Execution time is {result / n * 1e6} µs")
