import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/sensors")
async def get_sensors():
    # TODO: replace with real sensor readings
    return {
        "cpu_temp": 45.0 + random.random() * 5,
        "gpu_temp": 55.0 + random.random() * 5,
        "cpu_load": random.random(),
        "gpu_load": random.random(),
    }