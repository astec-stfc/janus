# import core.models.models as models
from typing import List
from time import perf_counter
import struct
import numpy as np
from fastapi import (
    BackgroundTasks,
    HTTPException,
    status,
    Depends,
    APIRouter,
    Request,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import uuid4
from core.database import get_db
from core.models import Lattice as DBLattice, Markers
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
import core.singletons as singletons

router = APIRouter(prefix="/lattice", tags=["Lattice"])

BEAM_ARRAY_FIELDS = ("x", "y", "z", "cpx", "cpy", "cpz")
_NULL_ARRAY_SENTINEL = 0xFFFFFFFF


def _encode_beam_binary(beam: Beam) -> bytes:
    # Format:
    # [4 bytes magic: b'JBM1']
    # Repeated for each field x,y,z,cpx,cpy,cpz:
    #   [4 bytes uint32 count, 0xFFFFFFFF means null]
    #   [count * 4 bytes float32 little-endian]
    chunks = [b"JBM1"]
    for field_name in BEAM_ARRAY_FIELDS:
        values = getattr(beam, field_name)
        if values is None:
            chunks.append(struct.pack("<I", _NULL_ARRAY_SENTINEL))
            continue
        arr = np.asarray(values, dtype=np.float32)
        chunks.append(struct.pack("<I", int(arr.size)))
        chunks.append(arr.tobytes(order="C"))
    return b"".join(chunks)


def publish_lattice_ready(request_id: str, client_id: str) -> None:
    """Publish a Kafka message indicating that a new lattice is ready."""
    try:
        if singletons.kafka_producer:
            singletons.kafka_producer.send(
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
        if singletons.kafka_producer:
            singletons.kafka_producer.send(
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
        if singletons.kafka_producer:
            singletons.kafka_producer.send(
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
        t0 = perf_counter()
        db_lattice = convert_lattice_to_db_schema(lattice)
        t1 = perf_counter()
        db.add(db_lattice)
        t2 = perf_counter()
        db.commit()
        t3 = perf_counter()
        db.refresh(db_lattice)
        t4 = perf_counter()
        payload_count = len(db_lattice.array_payloads or [])
        total_payload_bytes = sum(len(payload.payload) for payload in db_lattice.array_payloads or [])
        print(
            "create_lattice timings ",
            f"uuid={lattice.uuid} ",
            f"convert={t1-t0:.3f}s ",
            f"add={t2-t1:.3f}s ",
            f"commit={t3-t2:.3f}s ",
            f"refresh={t4-t3:.3f}s ",
            f"payload_rows={payload_count} ",
            f"payload_mb={total_payload_bytes / (1024 * 1024):.2f}",
        )
        lattice_manager.set(lattice)
        background_tasks.add_task(
            publish_lattice_added,
            lattice_uuid=lattice.uuid,
            client_id=lattice.client_id,
            request_id=request_id,
        )
        return lattice_manager.get().without_large_float_arrays().model_dump()


@router.post(
    "/binary",
    status_code=status.HTTP_201_CREATED,
)
async def create_lattice_binary(
    request: Request,
    background_tasks: BackgroundTasks,
    client_id: str,
    request_id: str = None,
    db: Session = Depends(get_db),
):
    """Store a lattice received as raw binary transport bytes.

    This endpoint exists for the RestFrame -> lattice-api handoff so services do
    not have to decode a large lattice to a schema object and then re-encode it
    as JSON before storage. The binary payload is decoded once here and then fed
    into the normal DB conversion path.
    """
    binary_payload = await request.body()
    if not binary_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binary lattice payload is empty.",
        )

    try:
        lattice = Lattice.from_binary(binary_payload, arrays_as_lists=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid binary lattice payload: {exc}",
        )

    lattice.client_id = client_id

    flow_log(
        "G08 results.stored",
        "S6/6",
        client_id=lattice.client_id,
        request_id=request_id,
        current="POST /lattice/binary received, storing simulation results in DB, publishing to topic 'lattice_added'",
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

    t0 = perf_counter()
    db_lattice = convert_lattice_to_db_schema(lattice)
    t1 = perf_counter()
    db.add(db_lattice)
    t2 = perf_counter()
    db.commit()
    t3 = perf_counter()
    db.refresh(db_lattice)
    t4 = perf_counter()
    payload_count = len(db_lattice.array_payloads or [])
    total_payload_bytes = sum(len(payload.payload) for payload in db_lattice.array_payloads or [])
    print(
        "create_lattice timings ",
        f"uuid={lattice.uuid} ",
        f"convert={t1-t0:.3f}s ",
        f"add={t2-t1:.3f}s ",
        f"commit={t3-t2:.3f}s ",
        f"refresh={t4-t3:.3f}s ",
        f"payload_rows={payload_count} ",
        f"payload_mb={total_payload_bytes / (1024 * 1024):.2f}",
    )

    lattice_manager.set(lattice)
    background_tasks.add_task(
        publish_lattice_added,
        lattice_uuid=lattice.uuid,
        client_id=lattice.client_id,
        request_id=request_id,
    )

    return {
        "uuid": lattice.uuid,
        "client_id": lattice.client_id,
        "request_id": request_id,
        "stored": True,
    }


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
def get_lattice(
    uuid: str = None,
    include_array_data: bool = False,
    db: Session = Depends(get_db),
):
    if not uuid:
        if lattice_manager.get():
            lattice_obj = lattice_manager.get()
            if not include_array_data:
                lattice_obj = lattice_obj.without_large_float_arrays()
            return lattice_obj.model_dump()
        lattice = db.query(DBLattice).filter(
            DBLattice.facility == os.getenv("FACILITY", "CLARA")
        )
        last_lattice = lattice.order_by(None).order_by(DBLattice.id.desc()).first()
        if last_lattice:
            lattice_obj = convert_db_schema_to_lattice(last_lattice)
            if not include_array_data:
                lattice_obj = lattice_obj.without_large_float_arrays()
            return lattice_obj.model_dump()
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
            lattice_obj = convert_db_schema_to_lattice(lattice)
            if not include_array_data:
                lattice_obj = lattice_obj.without_large_float_arrays()
            return lattice_obj.model_dump()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No lattices in database with uuid: {uuid}",
        )
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "No lattices in database",
    )


@router.get(
    "/binary",
    status_code=status.HTTP_200_OK,
    response_class=Response,
)
def get_lattice_binary(uuid: str = None, db: Session = Depends(get_db)):
    """
    Fetch lattice as compressed binary format for efficient transport of large arrays.

    Returns: application/octet-stream with metadata + compressed float32 array data

    Format:
      [4 bytes: compression flag (0xFFFFFFFF = zstd compressed)]
      [4 bytes: metadata JSON length]
      [variable: metadata JSON]
      [variable: binary payload (array data)]
    """
    lattice_obj = None

    if not uuid:
        if lattice_manager.get():
            lattice_obj = lattice_manager.get()
        else:
            lattice = db.query(DBLattice).filter(
                DBLattice.facility == os.getenv("FACILITY", "CLARA")
            )
            last_lattice = lattice.order_by(None).order_by(DBLattice.id.desc()).first()
            if last_lattice:
                lattice_obj = convert_db_schema_to_lattice(last_lattice)
    else:
        lattice = (
            db.query(DBLattice)
            .filter(
                DBLattice.uuid == uuid,
                DBLattice.facility == os.getenv("FACILITY", "CLARA"),
            )
            .one_or_none()
        )
        if lattice:
            lattice_obj = convert_db_schema_to_lattice(lattice)

    if not lattice_obj:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No lattices in database",
        )

    # Reuse the shared binary codec so service-to-service transport and packed
    # DB payload storage both follow the same representation.
    binary_data = lattice_obj.to_binary(compress=True, compression_level=1)

    return Response(
        content=binary_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=lattice_{lattice_obj.uuid}.bin",
            "X-Lattice-UUID": lattice_obj.uuid or "",
        }
    )


@router.get(
    "/binary/metadata",
    status_code=status.HTTP_200_OK,
)
def get_lattice_binary_metadata(uuid: str = None, db: Session = Depends(get_db)):
    """
    Fetch only metadata for a lattice binary response.

    Useful for checking array dimensions without downloading full payload. The
    metadata manifest mirrors the payload layout used by the shared binary codec.
    """
    lattice_obj = None

    if not uuid:
        if lattice_manager.get():
            lattice_obj = lattice_manager.get()
        else:
            lattice = db.query(DBLattice).filter(
                DBLattice.facility == os.getenv("FACILITY", "CLARA")
            )
            last_lattice = lattice.order_by(None).order_by(DBLattice.id.desc()).first()
            if last_lattice:
                lattice_obj = convert_db_schema_to_lattice(last_lattice)
    else:
        lattice = (
            db.query(DBLattice)
            .filter(
                DBLattice.uuid == uuid,
                DBLattice.facility == os.getenv("FACILITY", "CLARA"),
            )
            .one_or_none()
        )
        if lattice:
            lattice_obj = convert_db_schema_to_lattice(lattice)

    if not lattice_obj:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No lattices in database",
        )

    return lattice_obj.binary_metadata()


@router.get(
    "/request/{request_id}",
    status_code=status.HTTP_200_OK,
    response_model=Lattice,
)
def get_lattice_request(request_id: str):
    """Return the pending in-memory lattice request for RestFrame submission.

    This request path still uses the schema object directly because it carries
    settings into RestFrame before any tracking output exists to serialize.
    """
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

@router.get("/markers/names/", response_model=List[str])
def get_marker_names(
    uuid: str = None,
    db: Session = Depends(get_db),
):
    db_lattice = None
    current_lattice = lattice_manager.get()
    if current_lattice and (uuid is None or current_lattice.uuid == uuid):
        current_marker_names = [
            marker.name
            for section in current_lattice.sections.values()
            for marker in (section.markers or [])
        ]
        if current_marker_names:
            return current_marker_names

        # Some in-memory lattices (e.g. settings-only updates) may not include markers.
        # Fall back to persisted DB lattice for the requested uuid.
        if uuid:
            db_lattice = (
                db.query(DBLattice)
                .filter(
                    DBLattice.uuid == uuid,
                    DBLattice.facility == os.getenv("FACILITY", "CLARA"),
                )
                .one_or_none()
            )

    if uuid:
        db_lattice = db_lattice or (
            db.query(DBLattice)
            .filter(
                DBLattice.uuid == uuid,
                DBLattice.facility == os.getenv("FACILITY", "CLARA"),
            )
            .one_or_none()
        )
    else:
        db_lattice = (
            db.query(DBLattice)
            .filter(DBLattice.facility == os.getenv("FACILITY", "CLARA"))
            .order_by(None)
            .order_by(DBLattice.id.desc())
            .first()
        )

    if not db_lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"No lattice found with uuid: {uuid}" if uuid else "No lattices in database"),
        )

    return [
        marker.name
        for section in db_lattice.sections
        for marker in (section.markers or [])
    ]

@router.get("/screen/beam/", response_model=Beam)
def get_screen_beam(
    uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    current_lattice = lattice_manager.get()
    if current_lattice and current_lattice.uuid == uuid:
        for section in current_lattice.sections.values():
            for screen in section.screens:
                if screen.name == name:
                    if screen.beam is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No beam data for screen '{name}' in lattice uuid: {uuid}",
                        )
                    return screen.beam

    db_lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
    if not db_lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lattice found with uuid: {uuid}",
        )

    lattice = convert_db_schema_to_lattice(db_lattice)
    for section in lattice.sections.values():
        for screen in section.screens:
            if screen.name == name:
                if screen.beam is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No beam data for screen '{name}' in lattice uuid: {uuid}",
                    )
                return screen.beam
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No screen '{name}' found for lattice uuid: {uuid}",
    )

@router.get(
    "/marker/beam/",
    response_model=Beam,
)
def get_marker_beam(
    uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    current_lattice = lattice_manager.get()
    if current_lattice and current_lattice.uuid == uuid:
        for section in current_lattice.sections.values():
            for marker in section.markers:
                if marker.name == name:
                    if marker.beam is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No beam data for marker '{name}' in lattice uuid: {uuid}",
                        )
                    return marker.beam

    db_lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
    if not db_lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lattice found with uuid: {uuid}",
        )

    lattice = convert_db_schema_to_lattice(db_lattice)
    for section in lattice.sections.values():
        for marker in section.markers:
            if marker.name == name:
                if marker.beam is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No beam data for marker '{name}' in lattice uuid: {uuid}",
                    )
                return marker.beam
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No marker '{name}' found for lattice uuid: {uuid}",
    )

@router.get(
    "/screen/beam/binary/",
    status_code=status.HTTP_200_OK,
    response_class=Response,
)
def get_screen_beam_binary(
    uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    current_lattice = lattice_manager.get()
    if current_lattice and current_lattice.uuid == uuid:
        for section in current_lattice.sections.values():
            for screen in section.screens:
                if screen.name == name:
                    if screen.beam is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No beam data for screen '{name}' in lattice uuid: {uuid}",
                        )
                    binary_data = _encode_beam_binary(screen.beam)
                    return Response(
                        content=binary_data,
                        media_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f"attachment; filename=beam_{uuid}_{name}.bin",
                            "X-Janus-Beam-Format": "JBM1",
                        },
                    )

    db_lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
    if not db_lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lattice found with uuid: {uuid}",
        )

    lattice = convert_db_schema_to_lattice(db_lattice)

    for section in lattice.sections.values():
        for screen in section.screens:
            if screen.name == name:
                if screen.beam is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No beam data for screen '{name}' in lattice uuid: {uuid}",
                    )
                binary_data = _encode_beam_binary(screen.beam)
                return Response(
                    content=binary_data,
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f"attachment; filename=beam_{uuid}_{name}.bin",
                        "X-Janus-Beam-Format": "JBM1",
                    },
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No screen '{name}' found for lattice uuid: {uuid}",
    )

@router.get(
    "/marker/beam/binary/",
    status_code=status.HTTP_200_OK,
    response_class=Response,
)
def get_marker_beam_binary(
    uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    current_lattice = lattice_manager.get()
    if current_lattice and current_lattice.uuid == uuid:
        for section in current_lattice.sections.values():
            for marker in section.markers:
                if marker.name == name:
                    if marker.beam is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No beam data for marker '{name}' in lattice uuid: {uuid}",
                        )
                    binary_data = _encode_beam_binary(marker.beam)
                    return Response(
                        content=binary_data,
                        media_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f"attachment; filename=beam_{uuid}_{name}.bin",
                            "X-Janus-Beam-Format": "JBM1",
                        },
                    )

    db_lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
    if not db_lattice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lattice found with uuid: {uuid}",
        )

    lattice = convert_db_schema_to_lattice(db_lattice)

    for section in lattice.sections.values():
        for marker in section.markers:
            if marker.name == name:
                if marker.beam is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No beam data for marker '{name}' in lattice uuid: {uuid}",
                    )
                binary_data = _encode_beam_binary(marker.beam)
                return Response(
                    content=binary_data,
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f"attachment; filename=beam_{uuid}_{name}.bin",
                        "X-Janus-Beam-Format": "JBM1",
                    },
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No marker '{name}' found for lattice uuid: {uuid}",
    )

@router.get("/magnets/names/", response_model=List[str])
def get_magnet_names(
    db: Session = Depends(get_db),
):
    stmt = select(Magnets.name).distinct()
    magnet_names = db.scalars(stmt).all()
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
