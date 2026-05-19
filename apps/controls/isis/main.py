from p4p.server import Server
from janus_common.pv.builder import Builder


def main():
    pv_builder = Builder()
    Server.forever(
        providers=[
            {
                "ISIS:SIM:SEED": pv_builder.make_shared_pv_from_type(int),
            },
        ],
    )


if __name__ == "__main__":
    main()
