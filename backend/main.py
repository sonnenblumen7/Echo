import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from models.database import init_db
from daemon.watchdog_daemon import watchdog_loop

from routers import heartbeat, status, config, contacts, sos, internal, sleep, auth, bind

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(watchdog_loop())
    logger.info("Echo API 启动，watchdog_daemon 已启动")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Echo API 关闭")


app = FastAPI(title="Echo API", version="0.1.0", lifespan=lifespan)

app.include_router(heartbeat.router)
app.include_router(status.router)
app.include_router(config.router)
app.include_router(contacts.router)
app.include_router(sos.router)
app.include_router(internal.router)
app.include_router(sleep.router)
app.include_router(auth.router)
app.include_router(bind.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
