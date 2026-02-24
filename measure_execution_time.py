import time
import functools


def measure_time(func):
    """Decorator to measure and print execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed = end - start
        print(f"{func.__name__} took {elapsed:.6f} seconds")
        return result
    return wrapper


def time_it(func, *args, **kwargs):
    """Measure execution time of a callable with given arguments."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    elapsed = end - start
    return result, elapsed


if __name__ == "__main__":
    @measure_time
    def example_sleep():
        time.sleep(0.1)

    @measure_time
    def example_sum(n):
        return sum(range(n))

    example_sleep()
    example_sum(1_000_000)

    result, elapsed = time_it(sorted, [3, 1, 4, 1, 5, 9, 2, 6])
    print(f"sorted() took {elapsed:.6f} seconds, result: {result}")
