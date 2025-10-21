import functools
from asyncio import iscoroutinefunction
from time import time
from typing import Callable
from opticapa.shared.utils.logger import logger

def timer_func(func: Callable):
    """
    :param func:
    :return:
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Suppose that `function_name` is passed as a keyword argument
        function_name = kwargs.get("function_name", func.__name__)
        t1 = time()
        result = await func(*args, **kwargs)
        t2 = time()
        logger.warning(f"Function {function_name!r} executed in {(t2 - t1):.4f}s")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Suppose that `function_name` is passed as a keyword argument
        function_name = kwargs.get("function_name", func.__name__)
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        logger.warning(f"Function {function_name!r} executed in {(t2 - t1):.4f}s")
        return result

    return async_wrapper if iscoroutinefunction(func) else sync_wrapper