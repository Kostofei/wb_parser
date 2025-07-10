import time
from functools import wraps

def timeit(func):
    """
    Декоратор для измерения времени выполнения функции.

    Аргументы:
        func (function): Функция, время выполнения которой нужно измерить.

    Возвращает:
        function: Обёрнутая функция с измерением времени выполнения.
    """
    @wraps(func)  # сохраняем метаданные оригинальной функции
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f'Общее время выполнения функции {func.__name__} = {end_time - start_time:.4f} seconds')
        return result
    return wrapper