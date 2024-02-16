from fastapi import FastAPI, HTTPException, APIRouter, Body, Query
import pandas as pd
import numpy as np
# import random
# from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
# import numpy as np
from joblib import load
# from datetime import datetime, timedelta
# import uuid
from dotenv import load_dotenv
# import os
# import redis
# from fastapi.encoders import jsonable_encoder
# from fastapi.responses import JSONResponse
# from httpx import AsyncClient, Timeout
from typing import Optional, Union
# from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from exceptions.custom_exceptions import (
    DataSourceNotFoundException,
    DataSourceEmptyOrCorruptException,
    PageOutOfRangeException,
)
from exceptions.exception_handlers import (
    data_source_not_found_exception_handler,
    data_source_empty_or_corrupt_exception_handler,
    page_out_of_range_exception_handler,
)
import logging
import math

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("uvicorn")


load_dotenv()

description = """
BoxingData API. Retrieve stats on boxers by simple sending their full name🚀

## Fighter Stats

Send a valid boxer's full name and receive statistics pertaining to this boxer

Data was last updated in November 2019. Next update 19 November 2023
"""

tags_metadata = [
    {
        "name": "Fighter Stats",
        "description": "Send a valid boxer's full name and receive statisitcs on boxer. Ensure you conform to the format laid out below.",
    },
]


class FighterStats(BaseModel):
    name: str
    bouts_fought: int
    wins: Union[str, float]
    win_by_knockout: Optional[int] = 0
    losses: Union[str, float]
    average_weight: Union[str, float, None] = Field(default=None)


class Odds(BaseModel):
    win: float
    loss: float
    draw: float


class FightData(BaseModel):
    fighter1: FighterStats
    fighter2: FighterStats
    odds: Odds

app = FastAPI(openapi_tags=tags_metadata)
app = FastAPI(
    title="BoxingData",
    description=description,
    summary="Retrieve boxer stats",
    version="0.0.1",
    contact={
        "name": "Emmanuel Sibanda",
        "url": "https://emmanuelsibanda.vercel.app/",
        "email": "emmanuelsibandaus@gmail.com"
    },
    servers=[
        {"url": "https://boxingdata.onrender.com/"}
    ],
    openapi_tags=tags_metadata
)


url = "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/readdata.csv"
data = pd.read_csv(url)

router = APIRouter()


router.add_route("/docs", get_swagger_ui_html,
                 include_in_schema=False, name="swagger-ui")


app.include_router(router)

class FighterNames(BaseModel):
    fighter1: str
    fighter2: str


class FighterName(BaseModel):
    name: str = Field(
        ...,
        title="Fighter Name",
        description="The name of the fighter.",
        min_length=1,
        pattern="^[a-zA-Z0-9 ]+$",  
    )

app.exception_handler(DataSourceNotFoundException)(data_source_not_found_exception_handler)
app.exception_handler(DataSourceEmptyOrCorruptException)(data_source_empty_or_corrupt_exception_handler)
app.exception_handler(PageOutOfRangeException)(page_out_of_range_exception_handler)

@app.get(
    "/get_all_fighter_stats",
    include_in_schema=True,
responses={
        200: {
            "description": "Return all fighters' stats",
            "content": {
                "application/json": {
                    "example": {
                        "total_items": 100,
                        "total_pages": 10,
                        "skip": 0,
                        "limit": 10,
                        "data": [
                            {
                                "name": "Tyson Fury",
                                "wins": 30,
                                # Additional fighter stats...
                            }
                            # Additional fighters...
                        ],
                    }
                }
            }
        },
        404: {
            "description": "Data source not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Data source not found."}
                }
            }
        },
        422: {
            "description": "Data source is empty or corrupt",
            "content": {
                "application/json": {
                    "example": {"detail": "Data source is empty or corrupt."}
                }
            }
        },
        400: {
            "description": "Page number out of range",
            "content": {
                "application/json": {
                    "example": {"detail": "Page number out of range."}
                }
            }
        },
        500: {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while fetching the data."}
                }
            }
        }
    },    
    description="Return all boxer stats as paginated results",
    summary="Get All Boxer Stats",
    response_model=list, 
    tags=["Fighter Stats"]
)
async def get_all_fighter_stats(page: int = Query(default=1, ge=1), limit: int = Query(default=10, ge=1)):
    try:
        logger.debug(f"Fetching data for page {page} with limit {limit}")
        try:
            data_url = "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/topten.csv"
            data = pd.read_csv(data_url)
            logger.debug("Data fetched successfully from the CSV.")
        except FileNotFoundError:
            logger.error("Data source not found.")
            raise DataSourceNotFoundException("Data source not found.")
        except pd.errors.EmptyDataError:
            logger.error("Data source is empty or corrupt.")
            raise DataSourceEmptyOrCorruptException("Data source is empty or corrupt.")
        
        data.replace([np.nan, np.inf, -np.inf], None, inplace=True)
        logger.debug("NaN, inf, and -inf values replaced with None.")

        total_items = len(data)
        total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)
        logger.debug(f"Total items: {total_items}, Total pages: {total_pages}")

        if page > total_pages:
            logger.error("Page number out of range.")
            raise PageOutOfRangeException("Page number out of range.")
                
        skip = (page - 1) * limit
        paginated_data = data.iloc[skip: skip + limit]
        data_list = paginated_data.to_dict(orient="records")

        response = {
            "total_items": total_items,
            "total_pages": total_pages,
            "skip": skip,
            "limit": limit,
            "data": data_list,
        }
        logger.debug(f"Response prepared: {response}")
        return JSONResponse(content=response)
    except (DataSourceNotFoundException, DataSourceEmptyOrCorruptException, PageOutOfRangeException) as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching the data: {str(e)}")


@app.post(
    "/get_fighter_stats",
    include_in_schema=True,
    responses={404: {"description": "Fighter Not Found"}},
    description="Send the name of a boxer and get their stats. This is based on data last updated in November 2019. The next update will be on the 19th of November 2023.",
    summary="Get Boxer Stats",
    response_model=dict,
    tags=["Fighter Stats"]
)
async def get_fighter_stats(fighter: FighterName = Body(..., example={"name": "Tyson Fury"})):
    logger.info(f"Request received for fighter stats: {fighter.name}")
    logger.info("Loading fighter data from CSV...")
    data = pd.read_csv(
        "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/topten.csv")
    fighter_data = data[data['name'].str.contains(
        fighter.name, case=False, na=False)]
    # Check if the fighter is found in the dataset
    if fighter_data.empty:
        logger.warning(f"No data found for fighter named {fighter['name']}.")
        raise HTTPException(
            status_code=404, detail=f"No data found for fighter named {fighter.name}. It's possible that the fighter does not exist or there is no available data.")
    stats = {
        "Data As Of": "November 2019",
        "name": fighter_data['name'].iloc[0],
        "wins": int(fighter_data['wins'].iloc[0]) if not pd.isna(fighter_data['wins'].iloc[0]) else "Missing Data",
        "draws": int(fighter_data['draws'].iloc[0]) if not pd.isna(fighter_data['draws'].iloc[0]) else "Missing Data",
        "losses": int(fighter_data['losses'].iloc[0]) if not pd.isna(fighter_data['losses'].iloc[0]) else "Missing Data",
        "location": str(fighter_data['location'].iloc[0]),
        "division": str(fighter_data['division'].iloc[0]),
        "Average Weight": float(fighter_data['average_weight'].iloc[0]) if not pd.isna(fighter_data['average_weight'].iloc[0]) else "Missing Data",
        "Opponent Average Weight": float(fighter_data['average_opponent_weight'].iloc[0]) if not pd.isna(fighter_data['average_opponent_weight'].iloc[0]) else "Missing Data",
        "opp_points": int(fighter_data['opp_points'].iloc[0]) if not pd.isna(fighter_data['opp_points'].iloc[0]) else "Missing Data",
        "bouts_fought": int(fighter_data['bouts_fought'].iloc[0]) if not pd.isna(fighter_data['bouts_fought'].iloc[0]) else "Missing Data",
        "win by knockout": int(fighter_data['win by knockout'].iloc[0]) if not pd.isna(fighter_data['win by knockout'].iloc[0]) else "Missing Data",
        "win by split decision": int(fighter_data['win by split decision'].iloc[0]) if not pd.isna(fighter_data['win by split decision'].iloc[0]) else "Missing Data",
        "win by technical knockout": int(fighter_data['win by technical knockout'].iloc[0]) if not pd.isna(fighter_data['win by technical knockout'].iloc[0]) else "Missing Data",
        "win by unanimous decision": int(fighter_data['win by unanimous decision'].iloc[0]) if not pd.isna(fighter_data['win by unanimous decision'].iloc[0]) else "Missing Data",
    }

    additional_url = "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/readdata.csv"
    additional_data = pd.read_csv(additional_url)
    additional_fighter_data = additional_data[additional_data['name'].str.contains(
        fighter.name, case=False, na=False)]

    if not additional_fighter_data.empty:
        stats["BoxRec Link"] = additional_fighter_data['players_links'].iloc[0]

    # Read punching stats CSV
    punching_stats_url = "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/punchingstats.csv"
    punching_stats_data = pd.read_csv(punching_stats_url)

    # Filter punching stats based on the provided fighter name
    punching_stats_fighter = punching_stats_data[punching_stats_data['name'].str.contains(
        fighter.name, case=False, na=False)]

    # Check if the fighter is found in the punching stats dataset
    if punching_stats_fighter.empty:
        raise HTTPException(
            status_code=404, detail=f"Punching stats for fighter named {fighter.name} not found.")

    # Extract punching stats and append to the existing stats dictionary
    stats["Punch Stats"] = {
        "Jab accuracy (%)": format_percent(punching_stats_fighter['Jab accuracy'].iloc[0]),
        "Power punch accuracy (%)": format_percent(punching_stats_fighter['Power punch accuracy'].iloc[0]),
        "Total punch accuracy (%)": format_percent(punching_stats_fighter['Total punch accuracy'].iloc[0]),
        "Avg Jabs landed": float(punching_stats_fighter['Avg Jabs landed'].iloc[0]) if not pd.isna(punching_stats_fighter['Avg Jabs landed'].iloc[0]) else "Missing Data",
        "Avg Power punches landed": float(punching_stats_fighter['Avg Power punches landed'].iloc[0]) if not pd.isna(punching_stats_fighter['Avg Power punches landed'].iloc[0]) else "Missing Data",
        "Percentage of Power Punches received": format_percent(punching_stats_fighter['% of Power punches landed against'].iloc[0]),
        "Percentage of Total Punches received": format_percent(punching_stats_fighter['% of Total punches landed against'].iloc[0]),
        "Percentage of Jabs received": format_percent(punching_stats_fighter['% of Jabs landed against'].iloc[0]),
        "Average Jabs received per fight": float(punching_stats_fighter['Avg Jabs landed against'].iloc[0]) if not pd.isna(punching_stats_fighter['Avg Jabs landed against'].iloc[0]) else "Missing Data",
        "Average Power punches received per fight": float(punching_stats_fighter['Avg Power punches landed against'].iloc[0]) if not pd.isna(punching_stats_fighter['Avg Power punches landed against'].iloc[0]) else "Missing Data",
        "Average Total punches received per fight": float(punching_stats_fighter['Avg Total punches landed against'].iloc[0]) if not pd.isna(punching_stats_fighter['Avg Total punches landed against'].iloc[0]) else "Missing Data",
    }

    for key, value in stats.items():
        if isinstance(value, float) and not math.isfinite(value):
            logger.error(f"Non-compliant float value detected: {key}: {value}")
            # Optionally, adjust the value to be compliant or handle the error
            stats[key] = None  # Adjust non-compliant floats to None or an appropriate value

    logger.debug(f"Final stats prepared for return: {stats}")

    return stats


def format_percent(value):
    try:
        val = float(value)
        if val == float('inf') or val == float('-inf') or val != val: 
            logger.debug(f"Non-compliant float value encountered: {val}")
            return "0.00%"
        return f"{val:.2f}%"
    except (ValueError, TypeError):
        return "Missing Data"