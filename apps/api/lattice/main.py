from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from kafka import KafkaProducer
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import os
import core.models as models
from core.database import engine
from v1.routers import lattice_v1
from gql.router import graphql_router

models.Base.metadata.create_all(bind=engine)

# Global Kafka producer
kafka_producer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global kafka_producer
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers="broker:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print("Kafka producer initialized")
    except Exception as e:
        print(f"Failed to initialize Kafka producer: {e}")

    yield

    # Shutdown
    if kafka_producer:
        try:
            kafka_producer.close()
            print("Kafka producer closed")
        except Exception as e:
            print(f"Error closing Kafka producer: {e}")


app = FastAPI(lifespan=lifespan)

app_v1 = FastAPI()

while True:
    try:
        conn = psycopg2.connect(
            host="lattice_db",
            database="janus",
            user="postgres",
            password="postgres",
            cursor_factory=RealDictCursor,
        )

        cursor = conn.cursor()
        print("Database connection was successful")
        break

    except Exception as error:
        print("Connecting to database failed")
        print("Error", error)
        time.sleep(2)

app_v1.include_router(lattice_v1.router)

# Include GraphQL router with a prefix
app.include_router(graphql_router, prefix="/graphql")


app.mount("/v1", app_v1)

if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")


# catch-all route for React Router - must be after all API routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serves the React SPA for all routes that aren't API endpoints.
    This allows React Router to handle client-side routing.
    """
    if full_path.startswith("v1/"):
        return {"error": "Not found"}

    # Serve index.html for all other routes
    if os.path.exists("dist/index.html"):
        return FileResponse("dist/index.html")
    return {"message": "Backend API - Frontend should run separately on port 5173"}


@app_v1.get("/")
def root_v1():
    """Used for the healthpoint check in docker-compose"""
    return {"message": "Hello World V1!"}
