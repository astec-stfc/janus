# Kafka Messaging

`JANUS` utilises the [Kafka - Python](https://kafka-python.readthedocs.io/en/master/) library to publish and consume messages via the kafka broker service. This method of orchestration allows asynchronous messaging between all containers.

The `Lattice` and `RESTFrame` APIs publish messages on the following topics:

- `Lattice`
  - `lattice_ready` - new settings have been made
  - `lattice_updated` - a previous lattice has been loaded from the database
  - `lattice_added` - a new lattice has been stored in the database
- `RESTFrame`
  - `tracking_started` - `SIMBA` tracking has started
  - `tracking finished` - `SIMBA` tracking has completed

The `Services` are responsbile for consuming those messages and acting accordingly.

`Services` subscriptions:
- `lattice-to-restframe`: `lattice_ready`
- `restframe-to-lattice`: `tracking_finished`
- `lattice-to-epics`: `lattice_updated`, `lattice_added`, `tracking_finished`

<div class="mermaid">
flowchart LR
    Lattice[Lattice]
    Kafka["Kafka Broker"]
    RESTFrame[RESTFrame]

    Lattice ==>|New Settings| Kafka
    Lattice ==>|New Results| Kafka
    Lattice ==>|Lattice Already Exists| Kafka
    RESTFrame ==>|Tracking Started| Kafka
    RESTFrame ==>|Tracking Finished| Kafka

    Kafka ==> |New Settings| lattice-to-restframe
    Kafka ==> |Tracking Started| lattice-to-epics
    Kafka ==> |Tracking Finished| restframe-to-lattice
    Kafka ==> |Lattice Already Exists| lattice-to-epics
    Kafka ==> |New Results| lattice-to-epics

    style update-PVs fill:none,stroke:none
    lattice-to-epics ==> update-PVs

    style start-tracking fill:none,stroke:none
    lattice-to-restframe ==> start-tracking

    style store-lattice fill:none,stroke:none
    restframe-to-lattice ==> store-lattice

    style Lattice fill:#6d157a,stroke:#a037b0,stroke-width:2px,color:#ffffff
    style RESTFrame fill:#8a067a, stroke:#c230b1,stroke-width:2px,color:#ffffff
    style lattice-to-restframe fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style lattice-to-epics fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style restframe-to-lattice fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style Kafka fill:#065c10,stroke:#43944c,stroke-width:2px,color:#ffffff
  </div>
