import argparse
import paho.mqtt.client as mqtt
import json
import queue
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from collections import defaultdict


def modtick(n):
    # Return generator yielding True every n calls, else False
    def f():
        i = 0
        while True:
            yield i == 0
            i = (i + 1) % n

    return f()


q = queue.Queue()

# mqtt callbacks
def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("Bad connection Returned code=", rc)


def on_message(client, userdata, message):
    m = json.loads(message.payload.decode("utf-8"))
    q.put(m)


def on_publish(client, userdata, mid):
    print("mid: " + str(mid))


def main():
    parser = argparse.ArgumentParser(
        description=("Receive smart meter values over mqtt and send to influxdb")
    )
    parser.add_argument(
        "--mqttbroker",
        default="127.0.0.1",
        type=str,
        help="mqtt broker IP",
    )
    parser.add_argument(
        "--mqttport",
        default=1883,
        type=int,
        help="mqtt broker port",
    )
    parser.add_argument("--mqttuser", default=None, type=str, help="mqtt username")
    parser.add_argument("--mqttpass", default=None, type=str, help="mqtt password")
    parser.add_argument(
        "--client_id", default="glowtoinflux", type=str, help="Client id for mqtt"
    )
    parser.add_argument("--influxtoken", type=str, help="influxdb token")
    parser.add_argument("--influxorg", type=str, help="infludb org")
    parser.add_argument("--influxbucket", type=str, help="influx bucket")
    parser.add_argument(
        "--influxserver",
        type=str,
        help="influx server",
    )
    parser.add_argument("--influxport", default=8086, type=int, help="influx port")
    args = parser.parse_args()

    mqtt_client = mqtt.Client(args.client_id)

    if args.mqttuser is not None:
        mqtt_client.username_pw_set(args.mqttuser, password=args.mqttpass)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish
    mqtt_client.on_message = on_message
    mqtt_client.connect(args.mqttbroker, port=args.mqttport)
    mqtt_client.subscribe("glow/#")

    mqtt_client.loop_start()

    with InfluxDBClient(
        url=f"{args.influxserver}:{args.influxport}",
        token=args.influxtoken,
        org=args.influxorg,
    ) as influx_client:
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        # Send data every 10 minutes, each enviro sends message every 5 seconds
        ticks = defaultdict(lambda: modtick(10 * 60 / 5))
        while True:
            m = q.get()
            print(m)
            print(m.keys())
            # if next(ticks[m["id"]]):
            #     for k in set(m) - {"id"}:
            #         data = f"{k},location=enviro_{m['id']} {k}={m[k]}"
            #         write_api.write(args.influxbucket, args.influxorg, data)


if __name__ == "__main__":
    main()
