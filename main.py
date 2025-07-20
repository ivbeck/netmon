from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from monitor import metric_store
from config import TARGETS
import csv
import io


import csv_logger  # start CSV logging thread


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "targets": TARGETS})


@app.get("/api/metrics/{target}")
async def get_metrics(target: str):
    if target not in metric_store.data:
        return {"error": "Invalid target"}
    return metric_store.get_metrics(target)


@app.get("/api/metrics/{target}/csv")
async def export_csv(target: str):
    if target not in metric_store.data:
        return Response(content="Invalid target", media_type="text/plain", status_code=400)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "latency_ms"])

    for record in metric_store.data[target]:
        writer.writerow([record["timestamp"], record["latency"]])

    csv_content = output.getvalue()
    output.close()

    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={target}.csv"})
