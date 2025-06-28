
from fastapi import FastAPI
from chainlit.utils import mount_chainlit
import uvicorn
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return RedirectResponse(url="/chainlit")

mount_chainlit(app=app, target="chainlit_ui/chainlit_app.py", path="/chainlit")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)