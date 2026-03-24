import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head><title>MathSolver v3.1 Backend</title></head>
        <body style="font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #000; color: #fff;">
            <h1 style="color: #6366f1;">MATHSOLVER v3.1</h1>
            <p>This backend is designed for <b>Docker SDK</b> deployment.</p>
            <p>API is running at <a href="/docs" style="color: #818cf8;">/docs</a></p>
            <hr style="width: 50%; opacity: 0.1;"/>
            <p style="font-size: 0.8em; color: #555;">Deployed via Antigravity Agentic Engine</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=True)
