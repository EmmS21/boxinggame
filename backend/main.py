from fastapi import FastAPI, HTTPException, Request, APIRouter, Body
import pandas as pd
import random
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
from joblib import load
from datetime import datetime, timedelta
import uuid
from dotenv import load_dotenv
import os
import redis
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from httpx import AsyncClient, Timeout
from typing import Optional, Union
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html

load_dotenv()

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


app = FastAPI(
    title="BoxingData",
    description="Send the name of a boxer and get their stats. This is based on data last updated in November 2019. The next update will be on the 19th of November 2023",
    summary="Retrieve boxer stats"
    version="0.0.1",
    contact={
        "name": "Emmanuel Sibanda",
        "url": "https://boxingdata.onrender.com",
        "email": "emmanuelsibandaus@gmail.com"

    }
)



# Connect to your Redis instance

app.add_middleware(
    CORSMiddleware,
    # The origin(s) that should be allowed to access the server. Adjust as necessary.
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

url = "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/readdata.csv"
data = pd.read_csv(url)

router = APIRouter()



async def openapi_json():

    return JSONResponse(
        content=get_openapi(
            title="Boxing Data",
            version="1.0.0",
            routes=app.routes,
        )
    )

router.add_route("/docs", get_swagger_ui_html,
                 include_in_schema=False, name="swagger-ui")

router.add_route("/openapi.json", openapi_json, include_in_schema=False)


app.include_router(router)


@app.middleware("http")
async def set_persistent_cookie(request: Request, call_next):
    response = await call_next(request)
    redis_client = redis.Redis(
        host=os.getenv('HOST'),
        port=11879,
        password=os.getenv('REDISPASS')
    )
    user_id = request.cookies.get("user_id")

    # Check if the user already has a specific cookie
    if not user_id:
        # Cookie does not exist, so set a new cookie
        expiry_date = datetime.utcnow() + timedelta(days=14)  # Cookie expires in 14 days
        formatted_expiry_date = expiry_date.strftime(
            "%a, %d %b %Y %H:%M:%S GMT")  # Format according to HTTP date format
        unique_id = str(uuid.uuid4())  # Generate a unique ID for the user
        response.set_cookie(key="user_id", value=unique_id,
                            expires=formatted_expiry_date, httponly=True, secure=True, samesite='None')
        redis_client.hset(unique_id, mapping={"last_updated": str(
            datetime.utcnow()), "balance": 10000})
    else:
        # Check if it's time to update the balance
        last_updated = datetime.strptime((redis_client.hget(
            user_id, "last_updated")).decode('utf-8'), '%Y-%m-%d %H:%M:%S.%f')
        if (datetime.utcnow() - last_updated) >= timedelta(days=7):
            new_balance = int(
                (redis_client.hget(user_id, "balance")).decode('utf-8')) + 10000
            redis_client.hset(user_id, mapping={"last_updated": str(
                datetime.utcnow()), "balance": new_balance})
    return response


class FighterNames(BaseModel):
    fighter1: str
    fighter2: str


class FighterName(BaseModel):
    name: str = Field(
        ...,
        title="Fighter Name",
        description="The name of the fighter.",
        min_length=1,
        pattern="^[a-zA-Z0-9 ]+$",  # Allow spaces in the name
    )


@app.get("/balance", include_in_schema=False)
async def get_balance(request: Request):
    user_id = request.cookies.get("user_id")
    redis_client = redis.Redis(
        host=os.getenv('HOST'),
        port=11879,
        password=os.getenv('REDISPASS')
    )
    if user_id:
        balance = (redis_client.hget(user_id, "balance")).decode('utf-8')
        return {"balance": balance}
    return {"balance": "Unknown User"}


@app.post("/start_fight", include_in_schema=False)
async def start_fight(fight_data: FightData):
    # Extract the necessary data from the fight_data
    print('fighters', fight_data)
    fighter1 = fight_data.fighter1
    fighter2 = fight_data.fighter2
    odds = fight_data.odds
    prompt_text = f"Fighter 1: {fighter1}, Fighter 2: {fighter2}, Odds: {odds}"
    try:
        with open('prompt.txt', 'r') as file:
            prompt_from_file = file.read()
            prompt_text += f"\n\n{prompt_from_file}"
    except FileNotFoundError:
        print("The file prompt.txt was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    # print('prompt', prompt_text)
    timeout = Timeout(55.0, connect=60.0)
    async with AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI')}"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a boxing enthusiast who gives a very detailed and technical breakdown of boxing matches, inserting historial references from prior fights."
                    },
                    {
                        "role": "user",
                        "content": prompt_text
                    },
                ],
                "temperature": 0,
                "max_tokens": 2048,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
            }
        )
        if response.is_error:
            raise HTTPException(status_code=response.status_code,
                                detail="Error from OpenAI API")

        # Process the response and return the result
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            last_message_content = result["choices"][-1]["message"]["content"]
            print('last', last_message_content)
            return {"response": last_message_content}

    #     # Handle the case where there is no valid response
    #     return {"response": "No response from the AI model."}


@app.get("/fightstoday", include_in_schema=False)
def get_random_fighters():
    unique_divisions = set(data['division'].unique().tolist())
    selected_divisions = set()
    while len(selected_divisions) < 3:
        division = random.choice(list(unique_divisions))
        division_data = data[data['division'] == division]
        # Check if the division has at least two fighters
        if len(division_data) >= 2:
            selected_divisions.add(division)
            # Remove the selected division from the unique_divisions set to ensure uniqueness
            unique_divisions.remove(division)

    selected_fighters = []
    for division in selected_divisions:
        division_data = data[data['division'] == division]
        random_fighter = division_data.sample().to_dict(orient='records')[0]
        selected_fighters.append(random_fighter)
        partner_data = division_data[
            (division_data['sex'] == random_fighter['sex']) &
            # Ensure it's a different fighter
            (division_data['id'] != random_fighter['id'])
        ]
        # If found, select a random fighter from the filtered data
        partner_fighter = partner_data.sample().to_dict(orient='records')[0]
        selected_fighters.append(partner_fighter)

    return selected_fighters


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
    data = pd.read_csv(
        "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/topten.csv")
    fighter_data = data[data['name'].str.contains(
        fighter.name, case=False, na=False)]

    # Check if the fighter is found in the dataset
    if fighter_data.empty:
        raise HTTPException(
            status_code=404, detail=f"No data found for fighter named {fighter.name}. It's possible that the fighter does not exist or there is no available data.")
    # Extract boxer stats
    stats = {
        "Data As Of": "November 2019",
        "name": fighter_data['name'].iloc[0],
        "wins": int(fighter_data['wins'].iloc[0]) if not pd.isna(fighter_data['wins'].iloc[0]) else "Missing Data",
        "draws": int(fighter_data['draws'].iloc[0]) if not pd.isna(fighter_data['draws'].iloc[0]) else "Missing Data",
        "losses": int(fighter_data['losses'].iloc[0]) if not pd.isna(fighter_data['losses'].iloc[0]) else "Missing Data",
        # Convert to string to ensure JSON compatibility
        "location": str(fighter_data['location'].iloc[0]),
        # Convert to string to ensure JSON compatibility
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

    # Check if the fighter is found in the additional dataset
    if not additional_fighter_data.empty:
        # Extract additional data and append to the existing stats dictionary
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

    return stats


def format_percent(value):
    return f"{float(value):.2f}%" if not pd.isna(value) else "Missing Data"


@app.post("/get_fighter_details", include_in_schema=False)
async def get_fighter_details(fighter_names: FighterNames):
    data = pd.read_csv(
        "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/topten.csv")
    data = data.where(pd.notnull(data), None)
    fighter_details = {}

    for fighter in [fighter_names.fighter1, fighter_names.fighter2]:
        fighter_row = data.loc[data['name'].str.contains(
            fighter, case=False, na=False)]
        if fighter_row.empty:
            raise HTTPException(
                status_code=404, detail=f"Fighter named {fighter} not found.")
        fighter_detail = {
            'bouts_fought': fighter_row.iloc[0]['bouts_fought'],
            'wins': f"Wins: {fighter_row.iloc[0]['wins']}",
            'win_by_knockout': fighter_row.iloc[0]['win by knockout'],
            'losses': f"Losses: {fighter_row.iloc[0]['losses']}",
            'average_weight': f"Average Weight: {fighter_row.iloc[0]['average_weight']}"
        }
        fighter_details[fighter] = fighter_detail
    for fighter, details in fighter_details.items():
        fighter_details[fighter] = {
            k: clean_nan_values(v) for k, v in details.items()}

    json_compliant_data = jsonable_encoder(fighter_details)
    return JSONResponse(content=json_compliant_data)


def clean_nan_values(value):
    if isinstance(value, float) and np.isnan(value):
        return None
    elif value == 'nan':
        return None
    return value


@app.post("/predict", include_in_schema=False)
async def predict_fighter(fighter_name: FighterNames):
    print('tru')
    print('fighters', fighter_name)
    data = pd.read_csv(
        "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/topten.csv", low_memory=False)
    second_data = pd.read_csv(
        "https://raw.githubusercontent.com/EmmS21/SpringboardCapstoneBoxingPredictionWebApp/master/boxingdata/visualsfull.csv", low_memory=False
    )
    data.fillna(0, inplace=True)
    second_data.fillna(0, inplace=True)

    fighter_stats = {}
    model_loaded = False
    try:
        random_forest_model = load('randomForest.pkl')
        # print("Class labels:", random_forest_model.classes_)

        model_loaded = True
    except FileNotFoundError as e:
        print(f"Model file not found: {e}")
        model_loaded = False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        model_loaded = False
    if not model_loaded:
        raise HTTPException(
            status_code=503, detail="Model could not be loaded.")

    predictions = {}
    for current_fighter in [fighter_name.fighter1, fighter_name.fighter2]:
        fighter_row = data.loc[data['name'].str.contains(
            current_fighter, case=False, na=False)]
        if fighter_row.empty:
            raise HTTPException(
                status_code=404, detail=f"Fighter named {current_fighter} not found.")
        win_ko = fighter_row.iloc[0]['win by knockout'] + \
            fighter_row.iloc[0]['win by technical knockout']
        win_other = fighter_row.iloc[0]['win by split decision'] + \
            fighter_row.iloc[0]['win by unanimous decision']
        ko_ratio = win_ko / (fighter_row.iloc[0]['wins']) if (
            fighter_row.iloc[0]['wins']) > 0 else 0

        opponent_name = fighter_name.fighter2 if current_fighter == fighter_name.fighter1 else fighter_name.fighter1
        opponent_rows = second_data.loc[second_data['opposition'].str.contains(
            opponent_name, case=False, na=False)]

        fighter_ko_data = second_data.loc[second_data['name'].str.contains(
            current_fighter, case=False, na=False)]
        fighter_ko_ratio = fighter_ko_data['KnockedOut ratio'].dropna(
        ).mean() if not fighter_ko_data.empty else 0

        fighter_data_row = data.loc[data['name'].str.contains(
            current_fighter, case=False, na=False)]
        fighter_draws = fighter_data_row['draws'].iloc[0] if not fighter_data_row.empty else 0

        fighter_losses_ko = second_data.loc[second_data['name'].str.contains(
            current_fighter, case=False, na=False), 'Loss KO']
        loss_ko_average = fighter_losses_ko.mean() if not fighter_losses_ko.empty else 0

        average_opp_last6 = opponent_rows['opp_last6'].dropna().mean(
        ) if not opponent_rows.empty else 0

        opp_stats = second_data[second_data['opposition'].str.contains(
            opponent_name, case=False, na=False)]
        mean_values = {
            'opp_winOther': opp_stats['opp_winOther'].dropna().mean(),
            'opp_KO ratio': opp_stats['opp_KO ratio'].dropna().mean(),
            'opp_winKO': opp_stats['opp_winKO'].dropna().mean(),
            'opp_loss': opp_stats['opp_loss'].dropna().mean(),
            'opp_lossOther': opp_stats['opp_lossOther'].dropna().mean(),
            'opp_win': opp_stats['opp_win'].dropna().mean(),
            'opp_lossKO': opp_stats['opp_lossKO'].dropna().mean(),
        }

        fighter_stats[current_fighter] = {
            'Win KO': win_ko,
            'Loss Other': fighter_row.iloc[0]['losses'],
            'Win Other': win_other,
            'KO ratio': ko_ratio,
            'opp_last6': average_opp_last6,
            "KnockedOut ratio": fighter_ko_ratio,
            "Draw": fighter_draws,
            "Loss KO": loss_ko_average
        }
        fighter_stats[current_fighter].update(mean_values)
        features_df = pd.DataFrame([fighter_stats[current_fighter]])

        column_order = ['opp_last6', 'opp_KO ratio', 'Win KO', 'opp_winOther', 'Loss Other', 'Loss KO',
                        'Win Other', 'KO ratio', 'opp_winOther', 'KnockedOut ratio', 'opp_winKO', 'opp_KO ratio', 'opp_loss',
                        'opp_lossOther', 'opp_win', 'Draw', 'opp_lossKO']
        features_df = features_df[column_order]
        features_df.fillna(0, inplace=True)
        prediction = random_forest_model.predict_proba(features_df)
        prediction_mapped = dict(
            zip(random_forest_model.classes_, prediction[0]))
        return prediction_mapped
