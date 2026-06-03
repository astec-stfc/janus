# import core.models.models as models
from typing import List
from fastapi import BackgroundTasks, HTTPException, status, Depends, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import uuid4
from core.database import get_db
from core.models import Lattice as DBLattice
from core.models import (
    Cameras,
    Magnets,
    BPMs,
    Cavities,
    Screens,
    Section,
)
import os
from janus_common.utils.flow_log import flow_log
from core.utilities import (
    convert_lattice_to_db_schema,
    convert_db_schema_to_lattice,
    lattice_manager,
)
from janus_common.schemas.elements import Lattice, Beam

router = APIRouter(prefix="/lattice", tags=["Lattice"])


def get_kafka_producer():
    """Get the Kafka producer instance from main module."""
    from main import kafka_producer

    return kafka_producer


def publish_lattice_ready(request_id: str, client_id: str) -> None:
    """Publish a Kafka message indicating that a new lattice is ready."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_ready",
                value={"request_id": request_id, "client_id": client_id},
            )
        else:
            print("Kafka producer not initialized")
    except Exception as e:
        print(f"Failed to publish lattice_ready message: {e}")


def publish_lattice_added(
    lattice_uuid: str, client_id: str, request_id: str = None
) -> None:
    """Publish a Kafka message indicating that a new lattice has been added."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_added",
                value={
                    "request_id": request_id,  # helps track where particular request has already been handled in l2e (stops duplicate SIM_STATUS -> 1)
                    "uuid": lattice_uuid,  # so l2e fetches correct lattice to update pvs with
                    "client_id": client_id,  # lets correct client's l2e service process message and ignore others
                },
            )
        else:
            print("Kafka producer not initialized")
    except Exception as e:
        print(f"Failed to publish lattice_added message: {e}")


def publish_lattice_updated(lattice_uuid: str, client_id: str = None) -> None:
    """Publish a Kafka message indicating that a lattice has been updated."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_updated",
                value={
                    "uuid": lattice_uuid,
                    "client_id": client_id,
                },
            )
            print(f"Published lattice_updated message for lattice uuid: {lattice_uuid}")
        else:
            print("Kafka producer not initialized")
    except Exception as e:
        print(f"Failed to publish lattice_updated message: {e}")


@router.patch(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Lattice,
)
def patch_lattice(
    lattice: Lattice,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # if two clients happen to update their lattices that happen to be identical at the same time,
    # then, without this `if` statement, both (identical) lattices will get different request_ids.
    # gql won't detect the identical lattices because the 1st may not be stored yet. 
    # However, in reality, this is almost always guaranteed to run since simulataneously patched identical lattices from each other
    # will always be different since client_id is stamped onto each lattice.
    # TODO: in future, consider moving gql filtering/matching from e2l to here and make lattice_v1 solely responsible
    #       for checking existing settings -> (if so:) lattice_ready published, (if not: then) queuing request if no request is active. 
    #       This will allow us to remove `_current` dependency.
    if lattice != lattice_manager.get():
        request_id = str(uuid4())
        if lattice.client_id:
            flow_log(
                "G02 api.accept",
                "S1/6",
                client_id=lattice.client_id,
                request_id=request_id,
                current=(
                    "PATCH /lattice received, storing lattice request in memory, "
                    "publishing to topic 'lattice_ready'"
                ),
                next_step="comm-to-restframe to consume from topic 'lattice_ready' and send to restframe",
            )
        if lattice is None:
            db_lattice = db.query(DBLattice)
            last_lattice = (
                db_lattice.order_by(None).order_by(DBLattice.id.desc()).first()
            )
            if last_lattice:
                lattice = last_lattice
        lattice_manager.set(lattice)
        lattice_manager.set_request(request_id, lattice)
        background_tasks.add_task(
            publish_lattice_ready,
            request_id=request_id,
            client_id=lattice.client_id,
        )
        return lattice_manager.get().model_dump()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=("Attempted to PATCH lattice with equivalent settings."),
    )


@router.patch(
    "/settings",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Lattice,
)
def patch_lattice_settings(
    lattice: Lattice,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if lattice is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No lattice provided to update settings.",
        )
    if lattice != lattice_manager.get():
        lattice_manager.set(lattice)
        background_tasks.add_task(
            publish_lattice_updated,
            lattice_uuid=lattice.uuid,
            client_id=lattice.client_id,
        )
        return lattice_manager.get().model_dump()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=("Attempted to PATCH lattice with equivalent settings."),
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Lattice,
)
def refresh_lattice(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_lattice = db.query(DBLattice)
    last_lattice = db_lattice.order_by(None).order_by(DBLattice.id.desc()).first()
    if last_lattice:
        lattice = last_lattice
        lattice_manager.set(lattice)
        background_tasks.add_task(
            publish_lattice_updated,
            lattice_uuid=lattice.uuid,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No lattice found in database to refresh.",
        )
    return lattice_manager.get().model_dump()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=Lattice,
)
def create_lattice(
    lattice: Lattice,
    background_tasks: BackgroundTasks,
    request_id: str = None,
    db: Session = Depends(get_db),
):
    if lattice.client_id:
        flow_log(
            "G08 results.stored",
            "S6/6",
            client_id=lattice.client_id,
            request_id=request_id,
            current="POST /lattice received, storing simulation results in DB, publishing to topic 'lattice_added'",
            next_step="lattice-to-epics to consume from topic 'lattice_added' and write results to EPICS PVs",
        )
    get_lattice = db.query(DBLattice.id).filter(DBLattice.uuid == lattice.uuid)
    if db.query(get_lattice.exists()).scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Lattice with uuid: {lattice.uuid} already exists. To"
                " modify lattice please use PATCH request."
            ),
        )
    else:
        db_lattice = convert_lattice_to_db_schema(lattice)
        db.add(db_lattice)
        db.commit()
        db.refresh(db_lattice)
        lattice_manager.set(lattice)
        background_tasks.add_task(
            publish_lattice_added,
            lattice_uuid=lattice.uuid,
            client_id=lattice.client_id,
            request_id=request_id,
        )
        return convert_db_schema_to_lattice(db_lattice).model_dump()


@router.get("/uuid/latest", status_code=status.HTTP_200_OK, response_model=str)
def get_latest_uuid(db: Session = Depends(get_db)) -> str:
    current_lattice = lattice_manager.get()
    if current_lattice:
        return current_lattice.uuid

    lattice = db.query(DBLattice).filter(
        DBLattice.facility == os.getenv("FACILITY", "CLARA")
    )
    last_lattice = lattice.order_by(None).order_by(DBLattice.id.desc()).first()
    if last_lattice:
        return last_lattice.uuid

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "No lattices in database",
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Lattice,
)
def get_lattice(uuid: str = None, db: Session = Depends(get_db)):
    if not uuid:
        if lattice_manager.get():
            return lattice_manager.get().model_dump()
        lattice = db.query(DBLattice).filter(
            DBLattice.facility == os.getenv("FACILITY", "CLARA")
        )
        last_lattice = lattice.order_by(None).order_by(DBLattice.id.desc()).first()
        if last_lattice:
            return convert_db_schema_to_lattice(last_lattice)
    elif uuid:
        lattice = (
            db.query(DBLattice)
            .filter(
                DBLattice.uuid == uuid,
                DBLattice.facility == os.getenv("FACILITY", "CLARA"),
            )
            .one_or_none()
        )
        if lattice:
            return convert_db_schema_to_lattice(lattice).model_dump()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No lattices in database with uuid: {uuid}",
        )
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "No lattices in database",
    )


@router.get(
    "/request/{request_id}",
    status_code=status.HTTP_200_OK,
    response_model=Lattice,
)
def get_lattice_request(request_id: str):
    cached = lattice_manager.get_request(request_id=request_id)
    if cached:
        lattice_manager.remove_request(request_id)
        return cached.model_dump()
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"No pending lattice request with request_id: {request_id}",
    )


@router.get(
    "/runs",
    status_code=status.HTTP_200_OK,
    response_model=List[str],
)
def get_run_uuids(db: Session = Depends(get_db)):
    return [
        run[0]
        for run in db.query(DBLattice.uuid)
        .filter(
            DBLattice.facility
            == os.getenv(
                "FACILITY",
                "CLARA",
            )
        )
        .all()
    ]


@router.get("/cameras/names/", response_model=List[str])
def get_camera_names(
    db: Session = Depends(get_db),
):
    stmt = select(Cameras.name).distinct()
    camera_names = db.scalars(stmt).all()
    return camera_names


@router.get("/screens/names/", response_model=List[str])
def get_screen_names(
    uuid: str = None,
    db: Session = Depends(get_db),
):
    if uuid:
        lattice: DBLattice = (
            db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
        )
        if not lattice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No lattice found with uuid: {uuid}",
            )
        return list(
            screen.name for section in lattice.sections for screen in section.screens
        )
    stmt = select(Screens.name).distinct()
    return db.scalars(stmt).all()


@router.get("/screen/beam/", response_model=Beam)
def get_screen_beam(
    uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
    if not lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lattice found with uuid: {uuid}",
        )
    for section in lattice.sections:
        for screen in section.screens:
            if screen.name == name:
                if screen.beam is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No beam data for screen '{name}' in lattice uuid: {uuid}",
                    )
                return Beam.model_validate(screen.beam)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No screen '{name}' found for lattice uuid: {uuid}",
    )


@router.get("/magnets/names/", response_model=List[str])
def get_magnet_names(
    db: Session = Depends(get_db),
):
    stmt = select(Magnets.name).distinct()
    magnet_names = db.scalars(stmt)
    return magnet_names


@router.get("/bpms/names/", response_model=List[str])
def get_bpm_names(
    db: Session = Depends(get_db),
):
    stmt = select(BPMs.name).distinct()
    bpm_names = db.scalars(stmt).all()
    return bpm_names


@router.get("/cavities/names/", response_model=List[str])
def get_cavities_names(
    db: Session = Depends(get_db),
):
    stmt = select(Cavities.name).distinct()
    cavities_names = db.scalars(stmt).all()
    return cavities_names


@router.get("/sections/names/", response_model=List[str])
def get_sections_names(
    db: Session = Depends(get_db),
):
    stmt = select(Section.name).distinct()
    sections_names = db.scalars(stmt).all()
    return sections_names
