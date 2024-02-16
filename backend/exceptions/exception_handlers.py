from fastapi import Request
from fastapi.responses import JSONResponse
from .custom_exceptions import (
    DataSourceNotFoundException,
    DataSourceEmptyOrCorruptException,
    PageOutOfRangeException
)


async def data_source_not_found_exception_handler(request: Request, exc: DataSourceNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"error": "data_source_not_found", "message": exc.message},
    )

async def data_source_empty_or_corrupt_exception_handler(request: Request, exc: DataSourceEmptyOrCorruptException):
    return JSONResponse(
        status_code=400,
        content={"error": "data_source_empty_or_corrupt", "message": exc.message},
    )

async def page_out_of_range_exception_handler(request: Request, exc: PageOutOfRangeException):
    return JSONResponse(
        status_code=400,
        content={"error": "page_number_out_of_range", "message": exc.message},
    )

