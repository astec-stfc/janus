# import core.models.models as models
from typing import List
from fastapi import BackgroundTasks, HTTPException, status, Depends, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import select
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


def publish_lattice_ready(lattice_uuid: str) -> None:
    """Publish a Kafka message indicating that a new lattice is ready."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_ready", value={"uuid": lattice_uuid, "status": "ready"}
            )
            print(f"Published lattice_ready message for lattice uuid: {lattice_uuid}")
        else:
            print("Kafka producer not initialized")
    except Exception as e:
        print(f"Failed to publish lattice_ready message: {e}")


def publish_lattice_added(lattice_uuid: str) -> None:
    """Publish a Kafka message indicating that a new lattice has been added."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_added", value={"uuid": lattice_uuid, "status": "added"}
            )
            print(f"Published lattice_added message for lattice uuid: {lattice_uuid}")
        else:
            print("Kafka producer not initialized")
    except Exception as e:
        print(f"Failed to publish lattice_added message: {e}")


def publish_lattice_updated(lattice_uuid: str) -> None:
    """Publish a Kafka message indicating that a lattice has been updated."""
    try:
        producer = get_kafka_producer()
        if producer:
            producer.send(
                "lattice_updated", value={"uuid": lattice_uuid, "status": "updated"}
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
    if lattice != lattice_manager.get():
        if lattice is None:
            db_lattice = db.query(DBLattice)
            last_lattice = (
                db_lattice.order_by(None).order_by(DBLattice.id.desc()).first()
            )
            if last_lattice:
                lattice = last_lattice
        lattice_manager.set(lattice)
        background_tasks.add_task(
            publish_lattice_ready,
            lattice_uuid=lattice.uuid,
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
    db: Session = Depends(get_db),
):
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
        )
        return convert_db_schema_to_lattice(db_lattice).model_dump()


@router.get("/uuid/latest", status_code=status.HTTP_200_OK, response_model=str)
def get_latest_uuid() -> str:
    return lattice_manager.get().uuid


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
