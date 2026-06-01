from fastapi import FastAPI
from rpi4.api.routes import router
from rpi4.utils.logger import info

app = FastAPI(title="Calc Algebraica API")
app.include_router(router)


@app.on_event("startup")
def startup_event():
    info("Starting RPi calculator API")


@app.on_event("shutdown")
def shutdown_event():
    info("Stopping RPi calculator API")
