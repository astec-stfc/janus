from fastapi import FastAPI, Response
from app.services.hsds import HSDSClient
from app.models.exceptions import (
    DomainNotFoundError,
    GroupNotFoundError,
    DatasetNotFoundError,
    AttributeNotFoundError,
)
from threading import Thread
from app.services.watcher import start_watcher

app = FastAPI(
    title="HDF Portal",
    version="0.1.0",
)

hsds = HSDSClient()

@app.on_event("startup")
async def startup():

    thread = Thread(
        target=start_watcher,
        daemon=True,
    )
    thread.start()

@app.get("/")
def root():
    return {"service": "hdf-portal", "status": "ok"}


@app.get("/health")
def health():
    return hsds.health()


@app.get("/domain/")
def get_domain(domain: str):
    try:
        return hsds.get_domain(domain)
    except DomainNotFoundError as e:
        return {"error": str(e)}


@app.get("/domain/exists/")
def domain_exists(domain: str):
    return hsds.domain_exists(domain)


@app.get("/group/root/")
def get_root_group(domain: str):
    try:
        return hsds.get_group(domain, "/")
    except GroupNotFoundError as e:
        return {"error": str(e)}


@app.get("/group/")
def get_group(domain: str, path: str):
    try:
        return hsds.get_group(domain, path)
    except GroupNotFoundError as e:
        return {"error": str(e)}


@app.get("/group/members/")
def list_group_members(domain: str, path: str):
    try:
        return hsds.list_group_members(domain, path)
    except GroupNotFoundError as e:
        return {"error": str(e)}


@app.get("/dataset/")
def get_dataset(domain: str, path: str):
    try:
        return hsds.get_dataset_by_path(domain, path)
    except DatasetNotFoundError as e:
        return {"error": str(e)}


@app.get("/dataset/values/")
def get_dataset_values(
    domain: str,
    path: str,
    slice_start: int = None,
    slice_end: int = None,
):
    try:
        value = hsds.get_dataset_values_by_path(domain, path, slice_start, slice_end)
        if isinstance(value, bytes):
            return Response(
                content=value,
                media_type="application/octet-stream",
            )
        return value
    except DatasetNotFoundError as e:
        return {"error": str(e)}


@app.get("/attributes/")
def get_attributes(domain: str, path: str):
    try:
        return hsds.get_attributes(domain, path)
    except AttributeNotFoundError as e:
        return {"error": str(e)}
