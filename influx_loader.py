
import pandas as pd
import streamlit as st
from influxdb_client import InfluxDBClient

MEASUREMENT = "Sensor 1"
CAMPOS = ["temperatura", "humedad", "luz"]


def _query_flux(bucket: str, horas: int) -> str:
    filtro_campos = " or ".join(f'r._field == "{c}"' for c in CAMPOS)
    return f"""
from(bucket: "{bucket}")
  |> range(start: -{horas}h)
  |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
  |> filter(fn: (r) => {filtro_campos})
  |> pivot(rowKey: ["_time"], columnKeys: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", {", ".join(f'"{c}"' for c in CAMPOS)}])
  |> sort(columns: ["_time"])
"""


@st.cache_data(ttl=10, show_spinner="Consultando InfluxDB...")
def cargar_desde_influx(horas: int = 1) -> pd.DataFrame:
    cfg = st.secrets["influx"]  # url, token (SOLO LECTURA), org, bucket

    with InfluxDBClient(url=cfg["url"], token=cfg["token"], org=cfg["org"]) as client:
        resultado = client.query_api().query_data_frame(
            _query_flux(cfg["bucket"], horas)
        )

    # query_data_frame puede devolver una lista de DataFrames
    if isinstance(resultado, list):
        resultado = pd.concat(resultado, ignore_index=True) if resultado else pd.DataFrame()

    if resultado.empty:
        return resultado

    resultado = resultado.drop(columns=["result", "table"], errors="ignore")

    # UTC -> hora de Colombia, sin zona horaria para que Streamlit grafique bien
    resultado["_time"] = (
        pd.to_datetime(resultado["_time"], utc=True)
        .dt.tz_convert("America/Bogota")
        .dt.tz_localize(None)
    )
    return resultado
